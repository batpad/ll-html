import requests
import json
from datetime import datetime, timezone
from django.utils import timezone as django_timezone
from typing import Dict, List, Any, Optional
from .models import DataSource


class STACCatalogService:
    """Service for discovering and crawling STAC catalogs"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LL-HTML/1.0 STAC Crawler'
        })
    
    def discover_catalog(self, catalog_url: str) -> Dict[str, Any]:
        """
        Discover a STAC catalog and extract metadata
        Returns catalog information or raises exception
        """
        try:
            # Ensure URL ends with / for consistency
            catalog_url = catalog_url.rstrip('/') + '/'
            
            # Fetch catalog root
            response = self.session.get(catalog_url, timeout=self.timeout)
            response.raise_for_status()
            
            catalog_data = response.json()
            
            # Validate this is a STAC catalog
            if catalog_data.get('type') != 'Catalog':
                raise ValueError(f"URL does not point to a STAC Catalog (type: {catalog_data.get('type')})")
            
            # Extract basic catalog info
            catalog_info = {
                'id': catalog_data.get('id', 'unknown'),
                'title': catalog_data.get('title', ''),
                'description': catalog_data.get('description', ''),
                'stac_version': catalog_data.get('stac_version', ''),
                'conformance': self._get_conformance(catalog_url),
                'collections': self._discover_collections(catalog_url, catalog_data),
                'spatial_extent': self._calculate_overall_extent(),
                'temporal_extent': self._calculate_temporal_extent()
            }
            
            return catalog_info
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch STAC catalog: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from STAC catalog: {str(e)}")
    
    def _get_conformance(self, catalog_url: str) -> List[str]:
        """Get STAC conformance classes"""
        try:
            conformance_url = f"{catalog_url}conformance"
            response = self.session.get(conformance_url, timeout=self.timeout)
            if response.status_code == 200:
                conformance_data = response.json()
                return conformance_data.get('conformsTo', [])
        except:
            pass
        return []
    
    def _discover_collections(self, catalog_url: str, catalog_data: Dict) -> Dict[str, Any]:
        """Discover collections in the STAC catalog"""
        collections = {}
        
        # Try collections endpoint first
        try:
            collections_url = f"{catalog_url}collections"
            response = self.session.get(collections_url, timeout=self.timeout)
            if response.status_code == 200:
                collections_data = response.json()
                for collection in collections_data.get('collections', []):
                    collections[collection['id']] = self._process_collection(collection)
                return collections
        except:
            pass
        
        # Fallback: look for collection links in catalog
        for link in catalog_data.get('links', []):
            if link.get('rel') == 'child' and link.get('type') == 'application/json':
                try:
                    collection_url = link['href']
                    if not collection_url.startswith('http'):
                        collection_url = f"{catalog_url.rstrip('/')}/{collection_url.lstrip('/')}"
                    
                    response = self.session.get(collection_url, timeout=self.timeout)
                    if response.status_code == 200:
                        collection_data = response.json()
                        if collection_data.get('type') == 'Collection':
                            collections[collection_data['id']] = self._process_collection(collection_data)
                except:
                    continue
        
        return collections
    
    def _process_collection(self, collection_data: Dict) -> Dict[str, Any]:
        """Process a single collection and extract useful metadata"""
        return {
            'title': collection_data.get('title', ''),
            'description': collection_data.get('description', ''),
            'keywords': collection_data.get('keywords', []),
            'license': collection_data.get('license', ''),
            'extent': collection_data.get('extent', {}),
            'item_type': collection_data.get('item_type', 'Feature'),
            'properties': collection_data.get('summaries', {}),
            'providers': collection_data.get('providers', []),
        }
    
    def _calculate_overall_extent(self) -> Dict[str, Any]:
        """Calculate overall spatial extent from all collections"""
        # This is a placeholder - in real implementation we'd aggregate from collections
        return {}
    
    def _calculate_temporal_extent(self) -> Dict[str, Any]:
        """Calculate overall temporal extent from all collections"""
        # This is a placeholder - in real implementation we'd aggregate from collections
        return {}
    
    def create_data_source(self, catalog_url: str, category: str = 'geospatial') -> DataSource:
        """
        Create a DataSource from a STAC catalog URL
        """
        try:
            catalog_info = self.discover_catalog(catalog_url)
            
            # Create or update DataSource
            data_source, created = DataSource.objects.get_or_create(
                name=catalog_info['title'] or catalog_info['id'],
                defaults={
                    'description': catalog_info['description'],
                    'category': category,
                    'data_type': 'stac_catalog',
                    'base_url': catalog_url,
                    'stac_catalog_url': catalog_url,
                    'api_key_required': False,
                    'stac_collections': catalog_info['collections'],
                    'stac_conformance': catalog_info['conformance'],
                    'spatial_extent': catalog_info['spatial_extent'],
                    'temporal_extent': catalog_info['temporal_extent'],
                    'last_crawled': django_timezone.now(),
                    'data_format': 'STAC Items (GeoJSON)',
                    'is_active': True
                }
            )
            
            if not created:
                # Update existing record
                data_source.description = catalog_info['description']
                data_source.stac_collections = catalog_info['collections']
                data_source.stac_conformance = catalog_info['conformance']
                data_source.spatial_extent = catalog_info['spatial_extent']
                data_source.temporal_extent = catalog_info['temporal_extent']
                data_source.last_crawled = django_timezone.now()
                data_source.crawl_errors = ""
                data_source.save()
            
            # Generate LLM context and query patterns
            self._generate_llm_context(data_source)
            
            return data_source
            
        except Exception as e:
            # Update or create with error status
            data_source, created = DataSource.objects.get_or_create(
                name=f"STAC Catalog ({catalog_url})",
                defaults={
                    'description': f"STAC catalog at {catalog_url}",
                    'category': category,
                    'data_type': 'stac_catalog',
                    'base_url': catalog_url,
                    'stac_catalog_url': catalog_url,
                    'is_active': False,
                    'crawl_errors': str(e),
                    'last_crawled': django_timezone.now()
                }
            )
            
            if not created:
                data_source.crawl_errors = str(e)
                data_source.last_crawled = django_timezone.now()
                data_source.is_active = False
                data_source.save()
            
            raise e
    
    def _generate_llm_context(self, data_source: DataSource):
        """Generate rich LLM context from STAC catalog metadata"""
        collections = data_source.stac_collections
        
        context_parts = [
            f"**{data_source.name}** - STAC Catalog",
            data_source.description,
            f"Base URL: {data_source.base_url}",
            f"Search URL: {data_source.get_stac_search_url()}",
            ""
        ]
        
        if collections:
            context_parts.append("**Available Collections:**")
            for collection_id, collection_info in list(collections.items())[:10]:  # Limit to first 10
                title = collection_info.get('title', collection_id)
                desc = collection_info.get('description', '')
                context_parts.append(f"- {collection_id}: {title}")
                if desc and len(desc) < 100:
                    context_parts.append(f"  {desc}")
            
            if len(collections) > 10:
                context_parts.append(f"...and {len(collections) - 10} more collections")
        
        # Generate query patterns
        query_patterns = [
            {
                "name": "Search by bounding box",
                "template": "GET /search?collections={collection}&bbox={west},{south},{east},{north}",
                "description": "Find items within geographic bounds"
            },
            {
                "name": "Search by date range", 
                "template": "GET /search?collections={collection}&datetime={start_date}/{end_date}",
                "description": "Find items within time period"
            },
            {
                "name": "Combined spatial-temporal search",
                "template": "GET /search?collections={collection}&bbox={bbox}&datetime={datetime}",
                "description": "Find items by location and time"
            }
        ]
        
        # Generate widget templates
        widget_templates = [
            {
                "name": "Leaflet Map with STAC Items",
                "description": "Interactive map showing STAC item footprints and metadata",
                "libraries": ["leaflet", "leaflet-draw"],
                "example_code": "// Fetch STAC items and display on map with bounds"
            },
            {
                "name": "Timeline Chart",
                "description": "Chart.js timeline showing data availability over time",
                "libraries": ["chartjs"],
                "example_code": "// Create temporal distribution chart from STAC search results"
            }
        ]
        
        data_source.llm_context = "\n".join(context_parts)
        data_source.query_patterns = query_patterns
        data_source.widget_templates = widget_templates
        data_source.save()