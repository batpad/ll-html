from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json
import requests
from django.conf import settings
import logging
from datetime import datetime
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class AgentTool(ABC):
    """Base class for all agent tools"""
    
    def __init__(self):
        self.timeout = settings.AGENT_TOOL_TIMEOUT
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for LLM reference"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM understanding"""
        pass
    
    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON schema for tool parameters"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool and return results"""
        pass
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get OpenAI function calling format definition"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters_schema,
                "required": list(self.parameters_schema.keys())
            }
        }


class WebSearchTool(AgentTool):
    """Tool for searching the web for current information using DuckDuckGo"""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for current information about disasters, news, or specific topics. Returns recent web results with titles, descriptions, and URLs."
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "Search query (e.g. 'Bangladesh floods 2024', 'earthquake Turkey recent')"
            },
            "limit": {
                "type": "integer",
                "description": "Number of results to return (default: 5, max: 10)",
                "minimum": 1,
                "maximum": 10
            }
        }
    
    def execute(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Execute web search using DuckDuckGo via ddgs package"""
        try:
            from ddgs import DDGS
            
            results = []
            search_start = datetime.now()
            
            # Search for text results
            search_results = DDGS().text(
                query, 
                region='wt-wt',  # Worldwide
                safesearch='moderate',
                max_results=limit
            )
            
            for result in search_results:
                results.append({
                    "title": result.get('title', ''),
                    "description": result.get('body', ''),
                    "url": result.get('href', ''),
                    "source": self._extract_domain(result.get('href', '')),
                    "search_rank": len(results) + 1
                })
            
            search_time = (datetime.now() - search_start).total_seconds()
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_found": len(results),
                "search_time": f"{search_time:.3f}s",
                "search_engine": "DuckDuckGo"
            }
            
        except Exception as e:
            logger.error(f"Web search failed for query '{query}': {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "search_engine": "DuckDuckGo"
            }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for source attribution"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return "Unknown"


class ValidateAPITool(AgentTool):
    """Tool for validating API endpoints and checking data availability"""
    
    @property
    def name(self) -> str:
        return "validate_api_endpoint"
    
    @property
    def description(self) -> str:
        return "Validate an API endpoint and check its status, response format, and data availability."
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "url": {
                "type": "string", 
                "description": "API endpoint URL to validate"
            },
            "method": {
                "type": "string",
                "description": "HTTP method (default: GET)",
                "enum": ["GET", "POST"]
            }
        }
    
    def execute(self, url: str, method: str = "GET") -> Dict[str, Any]:
        """Validate API endpoint"""
        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                headers={'User-Agent': 'LL-HTML Agent/1.0'}
            )
            
            content_type = response.headers.get('content-type', '').lower()
            is_json = 'application/json' in content_type
            
            result = {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "is_accessible": response.status_code < 400,
                "content_type": content_type,
                "is_json": is_json,
                "response_size": len(response.content)
            }
            
            if is_json and response.status_code < 400:
                try:
                    data = response.json()
                    result["sample_structure"] = self._analyze_json_structure(data)
                except:
                    result["json_parse_error"] = True
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "url": url,
                "error": "Request timeout",
                "is_accessible": False
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "is_accessible": False
            }
    
    def _analyze_json_structure(self, data: Any, max_depth: int = 2) -> Dict[str, Any]:
        """Analyze JSON structure for the LLM"""
        if max_depth <= 0:
            return {"type": type(data).__name__}
        
        if isinstance(data, dict):
            return {
                "type": "object",
                "keys": list(data.keys())[:10],  # First 10 keys
                "sample_values": {
                    k: self._analyze_json_structure(v, max_depth - 1) 
                    for k, v in list(data.items())[:3]  # First 3 key-value pairs
                }
            }
        elif isinstance(data, list):
            return {
                "type": "array", 
                "length": len(data),
                "sample_item": self._analyze_json_structure(data[0], max_depth - 1) if data else None
            }
        else:
            return {"type": type(data).__name__, "sample": str(data)[:50]}


class FetchSTACDataTool(AgentTool):
    """Tool for fetching sample data from STAC catalogs"""
    
    @property
    def name(self) -> str:
        return "fetch_stac_sample_data"
    
    @property
    def description(self) -> str:
        return "Fetch sample data from a STAC catalog collection to understand data structure and availability."
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "collection": {
                "type": "string",
                "description": "STAC collection ID (e.g. 'gdacs-events', 'emdat-impacts')"
            },
            "bbox": {
                "type": "array",
                "description": "Bounding box [west, south, east, north] for geographic filtering",
                "items": {"type": "number"},
                "minItems": 4,
                "maxItems": 4
            },
            "limit": {
                "type": "integer", 
                "description": "Number of items to fetch (default: 5, max: 20)",
                "minimum": 1,
                "maximum": 20
            }
        }
    
    def execute(self, collection: str, bbox: List[float] = None, limit: int = 5) -> Dict[str, Any]:
        """Fetch sample STAC data"""
        try:
            from datasets.models import DataSource
            
            # Find STAC data sources
            stac_sources = DataSource.objects.filter(
                data_type='stac_catalog',
                is_active=True
            )
            
            if not stac_sources.exists():
                return {
                    "success": False,
                    "error": "No active STAC catalogs configured"
                }
            
            # Use first available STAC catalog
            source = stac_sources.first()
            search_url = source.get_stac_search_url()
            
            if not search_url:
                return {
                    "success": False,
                    "error": "STAC search URL not available"
                }
            
            # Build query parameters
            params = {
                "collections": collection,
                "limit": limit
            }
            
            if bbox:
                params["bbox"] = ",".join(map(str, bbox))
            
            # Make STAC search request
            response = requests.get(
                search_url,
                params=params,
                timeout=self.timeout,
                headers={'User-Agent': 'LL-HTML Agent/1.0'}
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"STAC API returned {response.status_code}",
                    "collection": collection
                }
            
            data = response.json()
            features = data.get('features', [])
            
            return {
                "success": True,
                "collection": collection,
                "search_url": search_url,
                "total_found": len(features),
                "bbox_used": bbox,
                "sample_features": [
                    {
                        "id": f.get('id'),
                        "geometry_type": f.get('geometry', {}).get('type'),
                        "properties": dict(list(f.get('properties', {}).items())[:5])  # First 5 properties
                    }
                    for f in features[:3]  # First 3 features
                ],
                "available_properties": list(features[0].get('properties', {}).keys()) if features else []
            }
            
        except Exception as e:
            logger.error(f"STAC data fetch failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "collection": collection
            }


class ValidateHTMLEndpointsTool(AgentTool):
    """Tool for validating API endpoints in generated HTML content"""
    
    @property
    def name(self) -> str:
        return "validate_html_endpoints"
    
    @property
    def description(self) -> str:
        return "Extract and validate all API endpoints found in HTML/JavaScript code to ensure they are accessible and working."
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "html_content": {
                "type": "string",
                "description": "HTML content containing JavaScript with API calls to validate"
            },
            "js_content": {
                "type": "string",
                "description": "JavaScript content with API calls to validate (optional)",
                "default": ""
            }
        }
    
    def execute(self, html_content: str, js_content: str = "") -> Dict[str, Any]:
        """Extract and validate all API endpoints in HTML/JS content"""
        try:
            # Combine HTML and JS content for analysis
            all_content = html_content + "\n" + js_content
            
            # Extract URLs from various JavaScript patterns
            urls = self._extract_urls_from_content(all_content)
            
            if not urls:
                return {
                    "success": True,
                    "urls_found": 0,
                    "valid_urls": [],
                    "invalid_urls": [],
                    "message": "No API endpoints found in content"
                }
            
            # Validate each URL
            valid_urls = []
            invalid_urls = []
            
            for url_info in urls:
                validation_result = self._validate_single_url(url_info["url"])
                url_info.update(validation_result)
                
                if validation_result["is_accessible"]:
                    valid_urls.append(url_info)
                else:
                    invalid_urls.append(url_info)
            
            return {
                "success": True,
                "urls_found": len(urls),
                "valid_urls": valid_urls,
                "invalid_urls": invalid_urls,
                "validation_summary": self._create_validation_summary(valid_urls, invalid_urls)
            }
            
        except Exception as e:
            logger.error(f"HTML endpoint validation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_urls_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract API URLs from HTML/JavaScript content"""
        urls = []
        
        # Patterns to match various JavaScript API call formats
        patterns = [
            # fetch() calls
            r"fetch\s*\(\s*['\"]([^'\"]+)['\"]",
            r"fetch\s*\(\s*`([^`]+)`",
            r"fetch\s*\(\s*([a-zA-Z_$][a-zA-Z0-9_$]*(?:\s*\+\s*['\"`][^'\"`]*['\"`])*)",
            
            # axios calls
            r"axios\.get\s*\(\s*['\"]([^'\"]+)['\"]",
            r"axios\.post\s*\(\s*['\"]([^'\"]+)['\"]",
            r"axios\(\s*['\"]([^'\"]+)['\"]",
            
            # XMLHttpRequest
            r"\.open\s*\(\s*['\"][^'\"]*['\"],\s*['\"]([^'\"]+)['\"]",
            
            # Direct URL assignments
            r"(?:const|let|var)\s+\w+\s*=\s*['\"]([^'\"]*(?:api|search|endpoint)[^'\"]*)['\"]",
            
            # STAC specific patterns
            r"['\"]([^'\"]*stac[^'\"]*search[^'\"]*)['\"]",
            r"['\"]([^'\"]*search[^'\"]*collections[^'\"]*)['\"]"
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                url = match.group(1).strip()
                
                # Skip obvious non-URLs
                if self._is_likely_url(url):
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(content), match.end() + 50)
                    context = content[context_start:context_end]
                    
                    urls.append({
                        "url": url,
                        "pattern": pattern,
                        "context": context.replace('\n', ' ').strip(),
                        "line_number": content[:match.start()].count('\n') + 1
                    })
        
        # Remove duplicates while preserving context
        unique_urls = []
        seen_urls = set()
        
        for url_info in urls:
            if url_info["url"] not in seen_urls:
                seen_urls.add(url_info["url"])
                unique_urls.append(url_info)
        
        return unique_urls
    
    def _is_likely_url(self, text: str) -> bool:
        """Check if text looks like a URL"""
        if not text or len(text) < 4:
            return False
        
        # Must start with http/https or be a relative path starting with /
        if not (text.startswith(('http://', 'https://', '/'))):
            return False
        
        # Must contain common API indicators
        api_indicators = ['api', 'search', 'endpoint', 'data', 'service', 'stac']
        return any(indicator in text.lower() for indicator in api_indicators)
    
    def _validate_single_url(self, url: str) -> Dict[str, Any]:
        """Validate a single URL"""
        try:
            # Handle relative URLs (assume HTTPS)
            if url.startswith('/'):
                # Can't validate relative URLs without base domain
                return {
                    "is_accessible": False,
                    "status_code": None,
                    "error": "Relative URL - cannot validate without base domain",
                    "response_time": None
                }
            
            # Validate URL format
            parsed = urlparse(url)
            if not parsed.netloc:
                return {
                    "is_accessible": False,
                    "status_code": None,
                    "error": "Invalid URL format",
                    "response_time": None
                }
            
            # Make request with timeout
            start_time = datetime.now()
            response = requests.head(  # Use HEAD to avoid downloading content
                url,
                timeout=self.timeout,
                headers={'User-Agent': 'LL-HTML URL Validator/1.0'},
                allow_redirects=True
            )
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "is_accessible": response.status_code < 400,
                "status_code": response.status_code,
                "error": None if response.status_code < 400 else f"HTTP {response.status_code}",
                "response_time": response_time,
                "final_url": response.url if response.url != url else None
            }
            
        except requests.exceptions.Timeout:
            return {
                "is_accessible": False,
                "status_code": None,
                "error": "Request timeout",
                "response_time": self.timeout
            }
        except requests.exceptions.RequestException as e:
            return {
                "is_accessible": False,
                "status_code": None,
                "error": str(e),
                "response_time": None
            }
    
    def _create_validation_summary(self, valid_urls: List[Dict], invalid_urls: List[Dict]) -> str:
        """Create a human-readable validation summary"""
        summary_parts = []
        
        if valid_urls:
            summary_parts.append(f"✅ {len(valid_urls)} valid endpoints:")
            for url_info in valid_urls[:5]:  # First 5
                summary_parts.append(f"  - {url_info['url']} ({url_info['status_code']})")
            if len(valid_urls) > 5:
                summary_parts.append(f"  ...and {len(valid_urls) - 5} more")
        
        if invalid_urls:
            summary_parts.append(f"❌ {len(invalid_urls)} invalid endpoints:")
            for url_info in invalid_urls[:5]:  # First 5  
                summary_parts.append(f"  - {url_info['url']} - {url_info['error']}")
            if len(invalid_urls) > 5:
                summary_parts.append(f"  ...and {len(invalid_urls) - 5} more")
        
        return "\n".join(summary_parts)


class ToolRegistry:
    """Registry for managing available agent tools"""
    
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools based on settings"""
        if settings.AGENT_ENABLE_WEB_SEARCH:
            self.register_tool(WebSearchTool())
        
        if settings.AGENT_ENABLE_API_VALIDATION:
            self.register_tool(ValidateAPITool())
            
        self.register_tool(FetchSTACDataTool())
        self.register_tool(ValidateHTMLEndpointsTool())
    
    def register_tool(self, tool: AgentTool):
        """Register a tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[AgentTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def get_available_tools(self) -> Dict[str, AgentTool]:
        """Get all available tools"""
        return self.tools.copy()
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI function calling format definitions for all tools"""
        return [tool.get_tool_definition() for tool in self.tools.values()]


# Global tool registry instance
tool_registry = ToolRegistry()