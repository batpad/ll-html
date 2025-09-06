from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    """Represents a project with version control for generated HTML pages"""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Git repository information
    repo_path = models.CharField(max_length=500, blank=True)
    git_url = models.URLField(blank=True)
    
    # Current active page
    current_page = models.OneToOneField(
        'generator.GeneratedPage', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='active_project'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-updated_at']


class PageVersion(models.Model):
    """Tracks different versions of a generated page"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='versions')
    generated_page = models.ForeignKey('generator.GeneratedPage', on_delete=models.CASCADE)
    
    version_number = models.PositiveIntegerField()
    commit_hash = models.CharField(max_length=40, blank=True)  # Git commit hash
    commit_message = models.TextField(blank=True)
    
    # What changed in this version
    change_summary = models.TextField(blank=True)
    files_changed = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.name} v{self.version_number}"
    
    class Meta:
        ordering = ['-version_number']
        unique_together = ['project', 'version_number']


class FileSnapshot(models.Model):
    """Stores snapshots of files at different versions"""
    
    version = models.ForeignKey(PageVersion, on_delete=models.CASCADE, related_name='files')
    file_path = models.CharField(max_length=500)
    file_content = models.TextField()
    file_type = models.CharField(max_length=50)  # html, css, js, etc.
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.file_path} (v{self.version.version_number})"
    
    class Meta:
        ordering = ['file_path']
