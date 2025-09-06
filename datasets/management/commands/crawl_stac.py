from django.core.management.base import BaseCommand, CommandError
from datasets.services import STACCatalogService
from datasets.models import DataSource


class Command(BaseCommand):
    help = 'Crawl STAC catalogs and populate DataSource records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'catalog_url',
            type=str,
            help='URL of the STAC catalog to crawl'
        )
        parser.add_argument(
            '--category',
            type=str,
            default='geospatial',
            help='Category for the data source (default: geospatial)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-crawl even if catalog was recently crawled'
        )
    
    def handle(self, *args, **options):
        catalog_url = options['catalog_url']
        category = options['category']
        force = options['force']
        
        self.stdout.write(f'Crawling STAC catalog: {catalog_url}')
        
        try:
            service = STACCatalogService()
            
            # Check if already exists and recently crawled
            if not force:
                existing = DataSource.objects.filter(
                    stac_catalog_url=catalog_url,
                    is_active=True
                ).first()
                
                if existing and existing.last_crawled:
                    from datetime import timedelta
                    from django.utils import timezone
                    if timezone.now() - existing.last_crawled < timedelta(hours=24):
                        self.stdout.write(
                            self.style.WARNING(
                                f'Catalog was crawled recently. Use --force to re-crawl.'
                            )
                        )
                        return
            
            # Crawl the catalog
            data_source = service.create_data_source(catalog_url, category)
            
            # Report results
            collections_count = len(data_source.get_available_collections())
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully crawled catalog: {data_source.name}\n'
                    f'  Collections found: {collections_count}\n'
                    f'  Data source ID: {data_source.id}\n'
                    f'  Search URL: {data_source.get_stac_search_url()}'
                )
            )
            
            # Show first few collections
            if collections_count > 0:
                self.stdout.write('\nCollections:')
                for collection_id in data_source.get_available_collections()[:5]:
                    collection_info = data_source.get_collection_info(collection_id)
                    title = collection_info.get('title', collection_id)
                    self.stdout.write(f'  - {collection_id}: {title}')
                
                if collections_count > 5:
                    self.stdout.write(f'  ...and {collections_count - 5} more')
            
        except Exception as e:
            raise CommandError(f'Failed to crawl STAC catalog: {str(e)}')