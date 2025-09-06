from django.db import models


class DataSource(models.Model):
    """Represents an external data source/API that the LLM can use"""
    
    CATEGORY_CHOICES = [
        ('weather', 'Weather & Climate'),
        ('emergency', 'Emergency & Disaster'),
        ('geological', 'Geological'),
        ('transportation', 'Transportation'),
        ('government', 'Government Services'),
        ('community', 'Community Resources'),
        ('geospatial', 'Geospatial & Remote Sensing'),
        ('other', 'Other'),
    ]
    
    DATA_TYPE_CHOICES = [
        ('rest_api', 'REST API'),
        ('stac_catalog', 'STAC Catalog'),
        ('wms', 'Web Map Service'),
        ('wfs', 'Web Feature Service'),
        ('rss', 'RSS Feed'),
        ('csv', 'CSV Data'),
        ('other', 'Other'),
    ]
    
    # Basic metadata
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, default='rest_api')
    base_url = models.URLField()
    api_key_required = models.BooleanField(default=False)
    documentation_url = models.URLField(blank=True)
    
    # API/Schema information
    api_schema = models.JSONField(default=dict, blank=True)
    example_queries = models.JSONField(default=list, blank=True)
    
    # STAC-specific fields
    stac_catalog_url = models.URLField(blank=True, help_text="STAC catalog root URL")
    stac_collections = models.JSONField(default=dict, blank=True, help_text="Available collections with metadata")
    stac_conformance = models.JSONField(default=list, blank=True, help_text="STAC conformance classes")
    
    # Geospatial metadata
    spatial_extent = models.JSONField(default=dict, blank=True, help_text="Geographic bounds (bbox)")
    temporal_extent = models.JSONField(default=dict, blank=True, help_text="Time range available")
    
    # LLM context information
    query_patterns = models.JSONField(default=list, blank=True, help_text="Common query templates for LLM")
    widget_templates = models.JSONField(default=list, blank=True, help_text="Visualization patterns")
    llm_context = models.TextField(blank=True, help_text="Rich description for LLM prompts")
    
    # Data characteristics
    update_frequency = models.CharField(max_length=50, blank=True, help_text="How often data is updated")
    data_format = models.CharField(max_length=50, blank=True, help_text="Primary data format (GeoJSON, COG, etc.)")
    license_info = models.CharField(max_length=100, blank=True)
    
    # Status and metadata
    is_active = models.BooleanField(default=True)
    last_crawled = models.DateTimeField(null=True, blank=True, help_text="Last time STAC catalog was crawled")
    crawl_errors = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def is_stac_catalog(self):
        """Check if this is a STAC catalog data source"""
        return self.data_type == 'stac_catalog'
    
    def get_stac_search_url(self):
        """Get the STAC search endpoint URL"""
        if not self.is_stac_catalog():
            return None
        base = self.stac_catalog_url or self.base_url
        return f"{base.rstrip('/')}/search"
    
    def get_available_collections(self):
        """Get list of available STAC collections"""
        return list(self.stac_collections.keys()) if self.stac_collections else []
    
    def get_collection_info(self, collection_id):
        """Get detailed info for a specific collection"""
        return self.stac_collections.get(collection_id, {})
    
    def get_llm_context_summary(self):
        """Generate rich context for LLM prompts"""
        if self.llm_context:
            return self.llm_context
            
        # Generate basic context if none provided
        context_parts = [f"**{self.name}** ({self.data_type.replace('_', ' ').title()})"]
        context_parts.append(self.description)
        
        if self.is_stac_catalog():
            collections = self.get_available_collections()
            if collections:
                context_parts.append(f"Collections: {', '.join(collections[:5])}")
                if len(collections) > 5:
                    context_parts.append(f"...and {len(collections) - 5} more")
        
        if self.spatial_extent:
            context_parts.append(f"Geographic coverage: {self.spatial_extent}")
        
        if self.temporal_extent:
            context_parts.append(f"Time range: {self.temporal_extent}")
            
        if self.update_frequency:
            context_parts.append(f"Updates: {self.update_frequency}")
            
        return "\n".join(context_parts)
    
    class Meta:
        ordering = ['category', 'name']


class DataQuery(models.Model):
    """Tracks queries made to external data sources"""
    
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    query_params = models.JSONField()
    response_data = models.JSONField(blank=True, null=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    # For caching and rate limiting
    query_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Query to {self.data_source.name} at {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']
