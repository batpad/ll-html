from django.contrib import admin
from django.utils.html import format_html
from .models import Project, PageVersion, FileSnapshot


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'current_page_title', 'version_count', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Project Info', {
            'fields': ('name', 'description', 'current_page')
        }),
        ('Git Repository', {
            'fields': ('repo_path', 'git_url'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def current_page_title(self, obj):
        if obj.current_page:
            return obj.current_page.title
        return "-"
    current_page_title.short_description = 'Current Page'
    
    def version_count(self, obj):
        return obj.versions.count()
    version_count.short_description = 'Versions'


@admin.register(PageVersion)
class PageVersionAdmin(admin.ModelAdmin):
    list_display = ['project', 'version_number', 'generated_page_title', 'commit_hash', 'file_count', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['commit_message', 'change_summary']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Version Info', {
            'fields': ('project', 'generated_page', 'version_number')
        }),
        ('Git Info', {
            'fields': ('commit_hash', 'commit_message')
        }),
        ('Changes', {
            'fields': ('change_summary', 'files_changed')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def generated_page_title(self, obj):
        return obj.generated_page.title if obj.generated_page else "-"
    generated_page_title.short_description = 'Page Title'
    
    def file_count(self, obj):
        return obj.files.count()
    file_count.short_description = 'Files'


@admin.register(FileSnapshot)
class FileSnapshotAdmin(admin.ModelAdmin):
    list_display = ['version', 'file_path', 'file_type', 'content_size', 'created_at']
    list_filter = ['file_type', 'created_at', 'version__project']
    search_fields = ['file_path', 'version__project__name']
    readonly_fields = ['created_at', 'content_preview']
    
    fieldsets = (
        ('File Info', {
            'fields': ('version', 'file_path', 'file_type')
        }),
        ('Content Preview', {
            'fields': ('content_preview',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def content_size(self, obj):
        return f"{len(obj.file_content)} chars"
    content_size.short_description = 'Size'
    
    def content_preview(self, obj):
        preview = obj.file_content[:500] + "..." if len(obj.file_content) > 500 else obj.file_content
        return format_html('<pre style="background: #f8f9fa; padding: 10px; max-height: 200px; overflow-y: auto; font-size: 12px;">{}</pre>', preview)
    content_preview.short_description = 'Content Preview'
