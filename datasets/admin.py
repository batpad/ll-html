from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import DataSource, DataQuery
import json


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'data_type', 'is_active', 'last_crawled', 
        'collections_count', 'has_errors', 'search_url_display'
    ]
    list_filter = ['category', 'data_type', 'is_active', 'last_crawled']
    search_fields = ['name', 'description', 'base_url']
    readonly_fields = ['created_at', 'updated_at', 'last_crawled']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'data_type', 'is_active')
        }),
        ('URLs and Access', {
            'fields': ('base_url', 'stac_catalog_url', 'documentation_url', 'api_key_required')
        }),
        ('STAC Specific', {
            'fields': ('stac_collections', 'stac_conformance'),
            'classes': ('collapse',)
        }),
        ('Geospatial Metadata', {
            'fields': ('spatial_extent', 'temporal_extent', 'data_format', 'license_info'),
            'classes': ('collapse',)
        }),
        ('LLM Context', {
            'fields': ('llm_context', 'query_patterns', 'widget_templates'),
            'classes': ('collapse',)
        }),
        ('API Schema', {
            'fields': ('api_schema', 'example_queries'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('update_frequency', 'last_crawled', 'crawl_errors', 'created_at', 'updated_at')
        })
    )
    
    def collections_count(self, obj):
        if obj.stac_collections:
            return len(obj.stac_collections)
        return 0
    collections_count.short_description = 'Collections'
    
    def has_errors(self, obj):
        if obj.crawl_errors:
            return format_html('<span style="color: red;">❌ Yes</span>')
        return format_html('<span style="color: green;">✅ No</span>')
    has_errors.short_description = 'Errors'
    
    def search_url_display(self, obj):
        if obj.is_stac_catalog():
            search_url = obj.get_stac_search_url()
            if search_url:
                return format_html('<a href="{}" target="_blank">{}</a>', search_url, search_url[:50] + '...')
        return '-'
    search_url_display.short_description = 'Search URL'
    
    actions = ['test_stac_connection', 'refresh_stac_metadata']
    
    def test_stac_connection(self, request, queryset):
        """Test STAC catalog connections"""
        from .services import STACCatalogService
        
        results = []
        service = STACCatalogService()
        
        for source in queryset.filter(data_type='stac_catalog'):
            try:
                catalog_info = service.discover_catalog(source.stac_catalog_url or source.base_url)
                results.append(f"✅ {source.name}: Found {len(catalog_info.get('collections', {}))} collections")
            except Exception as e:
                results.append(f"❌ {source.name}: {str(e)}")
        
        if results:
            self.message_user(request, "Connection test results:\n" + "\n".join(results))
        else:
            self.message_user(request, "No STAC catalogs selected.")
    
    test_stac_connection.short_description = "Test STAC connections"
    
    def refresh_stac_metadata(self, request, queryset):
        """Refresh STAC catalog metadata"""
        from .services import STACCatalogService
        
        service = STACCatalogService()
        updated = 0
        
        for source in queryset.filter(data_type='stac_catalog', is_active=True):
            try:
                updated_source = service.create_data_source(
                    source.stac_catalog_url or source.base_url, 
                    source.category
                )
                updated += 1
            except Exception as e:
                source.crawl_errors = str(e)
                source.save()
        
        self.message_user(request, f"Refreshed metadata for {updated} STAC catalogs.")
    
    refresh_stac_metadata.short_description = "Refresh STAC metadata"


@admin.register(DataQuery)
class DataQueryAdmin(admin.ModelAdmin):
    list_display = ['data_source', 'success', 'created_at', 'query_preview', 'response_size']
    list_filter = ['success', 'created_at', 'data_source']
    search_fields = ['query_hash', 'error_message']
    readonly_fields = ['query_hash', 'created_at']
    
    fieldsets = (
        ('Query Information', {
            'fields': ('data_source', 'query_params', 'query_hash')
        }),
        ('Response', {
            'fields': ('success', 'response_data', 'error_message')
        }),
        ('Metadata', {
            'fields': ('created_at',)
        })
    )
    
    def query_preview(self, obj):
        params = obj.query_params
        if isinstance(params, dict):
            preview = ", ".join([f"{k}={v}" for k, v in list(params.items())[:3]])
            return preview[:50] + "..." if len(preview) > 50 else preview
        return str(params)[:50]
    query_preview.short_description = 'Query Preview'
    
    def response_size(self, obj):
        if obj.response_data:
            return f"{len(str(obj.response_data))} chars"
        return "No response"
    response_size.short_description = 'Response Size'
