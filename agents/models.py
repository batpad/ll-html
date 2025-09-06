from django.db import models


class AgentSession(models.Model):
    """Represents a conversation session with the LLM agent"""
    
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    context = models.JSONField(default=dict)  # Conversation context and state
    
    # Current task state
    current_task = models.TextField(blank=True)
    task_status = models.CharField(max_length=50, default='idle')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session {self.session_id}"
    
    class Meta:
        ordering = ['-updated_at']


class AgentMessage(models.Model):
    """Individual messages in an agent session"""
    
    MESSAGE_TYPES = [
        ('user', 'User Input'),
        ('agent', 'Agent Response'),
        ('system', 'System Message'),
        ('tool', 'Tool Call Result'),
    ]
    
    session = models.ForeignKey(AgentSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    
    # For tool calls and structured responses
    metadata = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."
    
    class Meta:
        ordering = ['timestamp']


class AgentCapability(models.Model):
    """Defines what the agent knows how to do with different APIs/data sources"""
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Related data sources this capability can work with
    data_sources = models.ManyToManyField('datasets.DataSource', blank=True)
    
    # Prompt templates and instructions for this capability
    system_prompt = models.TextField()
    example_usage = models.JSONField(default=list, blank=True)
    
    # HTML templates this capability typically uses
    preferred_templates = models.ManyToManyField('generator.HTMLTemplate', blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
