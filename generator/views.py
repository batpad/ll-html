from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template import Template, Context
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import GeneratedPage, GenerationRequest, HTMLTemplate
from .serializers import GeneratePageSerializer, GeneratedPageSerializer
from agents.react_agent import ReactAgent
import os
import time


@api_view(['POST'])
def generate_page(request):
    """API endpoint to generate a new HTML page"""
    
    serializer = GeneratePageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user_request = serializer.validated_data['user_request']
    
    # Create generation request record
    generation_request = GenerationRequest.objects.create(
        user_input=user_request,
        llm_provider='openai',
        model_used='gpt-3.5-turbo'
    )
    
    try:
        start_time = time.time()
        
        # Use REACT agent to generate content with research
        agent = ReactAgent()
        agent_result = agent.execute(user_request)
        
        if not agent_result.get("success"):
            raise Exception(agent_result.get("error", "Agent execution failed"))
        
        content_data = agent_result["html_content"]
        
        # Debug: Print the content_data structure and agent info
        print(f"Agent completed in {agent_result.get('iterations_completed', 0)} iterations")
        print(f"LLM calls made: {agent_result.get('llm_calls_made', 0)}")
        print(f"Intelligence gathered: {agent_result.get('intelligence_used', 0)} tool results")
        print(f"Content data keys: {list(content_data.keys())}")
        print(f"Title: {content_data.get('title', 'MISSING')}")
        print(f"Main content preview: {str(content_data.get('main_content', 'MISSING'))[:100]}")
        
        # Load the basic template
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'basic_page.html')
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Create Django template and render with LLM-generated content
        template = Template(template_content)
        context = Context(content_data)
        html_content = template.render(context)
        
        generation_time = time.time() - start_time
        
        # Create the generated page record
        generated_page = GeneratedPage.objects.create(
            title=content_data.get('title', f'Page for: {user_request}'),
            user_request=user_request,
            html_content=html_content,
            status='completed',
            generation_time_seconds=generation_time,
            generation_prompt=f"User request: {user_request}"
        )
        
        # Link the generation request to the page
        generation_request.generated_page = generated_page
        generation_request.save()
        
        # Serialize and return the result
        page_serializer = GeneratedPageSerializer(generated_page)
        return Response({
            'success': True,
            'page': page_serializer.data,
            'generation_time': generation_time
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        # Mark as failed
        GeneratedPage.objects.create(
            title=f'Failed: {user_request}',
            user_request=user_request,
            status='failed',
            error_message=str(e)
        )
        
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_pages(request):
    """List all generated pages"""
    pages = GeneratedPage.objects.filter(status='completed').order_by('-created_at')[:20]
    serializer = GeneratedPageSerializer(pages, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_page(request, page_id):
    """Get details of a specific page"""
    page = get_object_or_404(GeneratedPage, id=page_id)
    serializer = GeneratedPageSerializer(page)
    return Response(serializer.data)


def view_page(request, page_id):
    """View the actual generated HTML page"""
    page = get_object_or_404(GeneratedPage, id=page_id, status='completed')
    return HttpResponse(page.html_content, content_type='text/html')


def demo_form(request):
    """Simple demo form for testing the generation"""
    return render(request, 'generator/demo_form.html')
