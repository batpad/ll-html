from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import HTMLTemplate, GeneratedPage, GenerationRequest
import json


@admin.register(HTMLTemplate)
class HTMLTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'library_count', 'created_at']
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'template_type', 'description', 'is_active')
        }),
        ('Template Content', {
            'fields': ('template_content',)
        }),
        ('Styling & Scripts', {
            'fields': ('css_template', 'js_template'),
            'classes': ('collapse',)
        }),
        ('External Libraries', {
            'fields': ('required_libraries',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        })
    )
    
    def library_count(self, obj):
        if obj.required_libraries:
            return len(obj.required_libraries)
        return 0
    library_count.short_description = 'Libraries'


@admin.register(GeneratedPage)
class GeneratedPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'template_used', 'data_sources_count', 'generation_time_seconds', 'created_at']
    list_filter = ['status', 'template_used', 'created_at']
    search_fields = ['title', 'user_request']
    readonly_fields = ['created_at', 'updated_at', 'view_page_link', 'html_preview']
    filter_horizontal = ['data_sources_used']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'user_request', 'status')
        }),
        ('Generation Details', {
            'fields': ('template_used', 'data_sources_used', 'generation_time_seconds', 'generation_prompt')
        }),
        ('Content', {
            'fields': ('html_preview', 'view_page_link'),
            'classes': ('collapse',)
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('File Storage', {
            'fields': ('file_path',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def data_sources_count(self, obj):
        return obj.data_sources_used.count()
    data_sources_count.short_description = 'Data Sources'
    
    def view_page_link(self, obj):
        if obj.status == 'completed':
            url = reverse('generator:view_page', args=[obj.id])
            return format_html('<a href="{}" target="_blank">View Generated Page</a>', url)
        return "Page not completed"
    view_page_link.short_description = 'View Page'
    
    def html_preview(self, obj):
        if obj.html_content and obj.status == 'completed':
            preview = obj.html_content[:500] + "..." if len(obj.html_content) > 500 else obj.html_content
            return format_html('<pre style="background: #f8f9fa; padding: 10px; max-height: 200px; overflow-y: auto; font-size: 12px;">{}</pre>', preview)
        return "No HTML content"
    html_preview.short_description = 'HTML Preview'


@admin.register(GenerationRequest)
class GenerationRequestAdmin(admin.ModelAdmin):
    list_display = ['user_input_preview', 'llm_provider', 'model_used', 'tokens_used', 'generated_page_link', 'created_at']
    list_filter = ['llm_provider', 'model_used', 'created_at']
    search_fields = ['user_input', 'processed_request']
    readonly_fields = ['created_at', 'generated_page_link']
    
    fieldsets = (
        ('Request Info', {
            'fields': ('user_input', 'processed_request')
        }),
        ('LLM Details', {
            'fields': ('llm_provider', 'model_used', 'tokens_used')
        }),
        ('Result', {
            'fields': ('generated_page_link',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def user_input_preview(self, obj):
        return obj.user_input[:50] + "..." if len(obj.user_input) > 50 else obj.user_input
    user_input_preview.short_description = 'User Input'
    
    def generated_page_link(self, obj):
        if obj.generated_page:
            url = reverse('admin:generator_generatedpage_change', args=[obj.generated_page.id])
            return format_html('<a href="{}">{}</a>', url, obj.generated_page.title)
        return "No page generated"
    generated_page_link.short_description = 'Generated Page'
