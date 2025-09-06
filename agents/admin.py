from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import AgentSession, AgentMessage, AgentCapability
import json


@admin.register(AgentSession)
class AgentSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'task_status', 'current_task_preview', 'message_count', 'created_at', 'updated_at']
    list_filter = ['task_status', 'created_at', 'updated_at']
    search_fields = ['session_id', 'current_task']
    readonly_fields = ['created_at', 'updated_at', 'context_display']
    
    fieldsets = (
        ('Session Info', {
            'fields': ('session_id', 'current_task', 'task_status')
        }),
        ('Context Data', {
            'fields': ('context_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def current_task_preview(self, obj):
        if obj.current_task:
            return obj.current_task[:50] + "..." if len(obj.current_task) > 50 else obj.current_task
        return "-"
    current_task_preview.short_description = 'Task Preview'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def context_display(self, obj):
        if obj.context:
            try:
                formatted = json.dumps(obj.context, indent=2)
                return format_html('<pre style="background: #f8f9fa; padding: 10px; max-height: 400px; overflow-y: auto;">{}</pre>', formatted)
            except:
                return str(obj.context)
        return "No context data"
    context_display.short_description = 'Context (JSON)'


@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'message_type', 'content_preview', 'timestamp']
    list_filter = ['message_type', 'timestamp', 'session__task_status']
    search_fields = ['content', 'session__session_id']
    readonly_fields = ['timestamp', 'metadata_display']
    
    fieldsets = (
        ('Message Info', {
            'fields': ('session', 'message_type', 'content')
        }),
        ('Metadata', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        })
    )
    
    def content_preview(self, obj):
        preview = obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
        if obj.message_type == 'tool':
            return format_html('<span style="color: blue; font-family: monospace;">{}</span>', preview)
        elif obj.message_type == 'agent':
            return format_html('<span style="color: green;">{}</span>', preview)
        elif obj.message_type == 'user':
            return format_html('<span style="color: purple;">{}</span>', preview)
        return preview
    content_preview.short_description = 'Content Preview'
    
    def metadata_display(self, obj):
        if obj.metadata:
            try:
                formatted = json.dumps(obj.metadata, indent=2)
                return format_html('<pre style="background: #f8f9fa; padding: 10px; max-height: 300px; overflow-y: auto;">{}</pre>', formatted)
            except:
                return str(obj.metadata)
        return "No metadata"
    metadata_display.short_description = 'Metadata (JSON)'


@admin.register(AgentCapability)
class AgentCapabilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'data_sources_count', 'templates_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    filter_horizontal = ['data_sources', 'preferred_templates']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('System Prompt', {
            'fields': ('system_prompt',)
        }),
        ('Relationships', {
            'fields': ('data_sources', 'preferred_templates')
        }),
        ('Examples', {
            'fields': ('example_usage',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        })
    )
    
    def data_sources_count(self, obj):
        return obj.data_sources.count()
    data_sources_count.short_description = 'Data Sources'
    
    def templates_count(self, obj):
        return obj.preferred_templates.count()
    templates_count.short_description = 'Templates'
