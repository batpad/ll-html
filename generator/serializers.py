from rest_framework import serializers
from .models import GeneratedPage, GenerationRequest


class GeneratePageSerializer(serializers.Serializer):
    """Serializer for page generation requests"""
    user_request = serializers.CharField(max_length=1000)
    
    
class GeneratedPageSerializer(serializers.ModelSerializer):
    """Serializer for generated page responses"""
    
    class Meta:
        model = GeneratedPage
        fields = [
            'id', 'title', 'user_request', 'status', 
            'html_content', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GenerationRequestSerializer(serializers.ModelSerializer):
    """Serializer for tracking generation requests"""
    
    class Meta:
        model = GenerationRequest
        fields = [
            'id', 'user_input', 'llm_provider', 'model_used', 
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']