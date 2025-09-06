from django.db import models
from django.contrib.auth.models import User


class HTMLTemplate(models.Model):
    """Base HTML templates for different types of disaster response apps"""
    
    TEMPLATE_TYPES = [
        ('dashboard', 'Data Dashboard'),
        ('map', 'Map Visualization'),
        ('table', 'Data Table'),
        ('alert', 'Alert System'),
        ('form', 'Data Entry Form'),
        ('report', 'Report Generator'),
        ('generic', 'Generic Page'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    description = models.TextField()
    
    # The base HTML template with placeholders
    template_content = models.TextField()
    
    # Required external libraries (CDN links)
    required_libraries = models.JSONField(default=list, blank=True)
    
    # CSS and JS template snippets
    css_template = models.TextField(blank=True)
    js_template = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"
    
    class Meta:
        ordering = ['template_type', 'name']


class GeneratedPage(models.Model):
    """Represents a generated HTML page"""
    
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    title = models.CharField(max_length=200)
    user_request = models.TextField()  # Original user request
    
    # Generation details
    template_used = models.ForeignKey(HTMLTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    data_sources_used = models.ManyToManyField('datasets.DataSource', blank=True)
    
    # Generated content
    html_content = models.TextField(blank=True)
    generation_prompt = models.TextField(blank=True)  # Prompt sent to LLM
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    error_message = models.TextField(blank=True)
    generation_time_seconds = models.FloatField(null=True, blank=True)
    
    # File system storage
    file_path = models.CharField(max_length=500, blank=True)  # Path to saved HTML file
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']


class GenerationRequest(models.Model):
    """Tracks the full generation process and LLM interactions"""
    
    user_input = models.TextField()
    processed_request = models.TextField(blank=True)  # Cleaned/processed version
    
    # LLM interaction
    llm_provider = models.CharField(max_length=50, default='openai')
    model_used = models.CharField(max_length=50, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    
    # Results
    generated_page = models.OneToOneField(GeneratedPage, on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Request: {self.user_input[:50]}..."
    
    class Meta:
        ordering = ['-created_at']
