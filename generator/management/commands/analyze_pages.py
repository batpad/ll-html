from django.core.management.base import BaseCommand
from django.utils import timezone
from generator.models import GeneratedPage
from agents.models import AgentSession
import json
import re
from urllib.parse import urlparse


class Command(BaseCommand):
    help = 'Analyze generated pages to identify URL and data source issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', 
            type=int, 
            default=5,
            help='Number of recent pages to analyze (default: 5)'
        )
        parser.add_argument(
            '--page-id',
            type=int,
            help='Analyze specific page by ID'
        )
        parser.add_argument(
            '--show-urls',
            action='store_true',
            help='Extract and show all URLs from generated content'
        )
        parser.add_argument(
            '--show-agent-details',
            action='store_true', 
            help='Show detailed agent session information'
        )

    def handle(self, *args, **options):
        if options['page_id']:
            pages = GeneratedPage.objects.filter(id=options['page_id'])
        else:
            pages = GeneratedPage.objects.all().order_by('-created_at')[:options['count']]

        if not pages:
            self.stdout.write(self.style.WARNING('No pages found'))
            return

        self.stdout.write(self.style.SUCCESS(f'Analyzing {len(pages)} pages:'))
        self.stdout.write('=' * 80)

        for page in pages:
            self.analyze_page(page, options)
            self.stdout.write('-' * 80)

    def analyze_page(self, page, options):
        self.stdout.write(self.style.HTTP_INFO(f'PAGE #{page.id}: {page.title}'))
        self.stdout.write(f'Created: {page.created_at}')
        self.stdout.write(f'Request: {page.user_request[:100]}...' if len(page.user_request) > 100 else f'Request: {page.user_request}')
        
        # Agent session analysis - check if there's a related generation request
        try:
            gen_request = page.generationrequest
            self.stdout.write(f'Generation Request ID: {gen_request.id}')
            self.stdout.write(f'LLM Provider: {gen_request.llm_provider}')
            self.stdout.write(f'Model: {gen_request.model_used}')
            self.stdout.write(f'Tokens: {gen_request.tokens_used or "Not recorded"}')
            
            # Check for agent sessions created during this time
            from agents.models import AgentSession
            recent_sessions = AgentSession.objects.filter(
                created_at__gte=gen_request.created_at,
                created_at__lte=page.created_at
            ).order_by('-created_at')[:1]
            
            if recent_sessions:
                session = recent_sessions[0]
                self.stdout.write(f'Likely Agent Session: {session.session_id}')
                if options['show_agent_details']:
                    self.show_agent_session_details(session)
            else:
                self.stdout.write(self.style.WARNING('No matching agent session found'))
                    
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'No generation request found: {e}'))

        # Content analysis - check both content_data and html_content
        content = None
        if hasattr(page, 'content_data') and page.content_data:
            try:
                content = json.loads(page.content_data) if isinstance(page.content_data, str) else page.content_data
                self.stdout.write(f'Content data fields: {list(content.keys()) if isinstance(content, dict) else "Invalid format"}')
            except:
                self.stdout.write(self.style.WARNING('Failed to parse content_data'))
        
        if page.html_content:
            self.stdout.write(f'HTML content length: {len(page.html_content)} characters')
            if not content and options['show_urls']:
                # Analyze HTML content directly if no structured content_data
                self.extract_and_analyze_urls({'html_content': page.html_content})
        
        if options['show_urls'] and content and isinstance(content, dict):
            self.extract_and_analyze_urls(content)

    def show_agent_session_details(self, session):
        self.stdout.write('\nAGENT SESSION DETAILS:')
        self.stdout.write(f'Session ID: {session.session_id}')
        self.stdout.write(f'Task Status: {session.task_status}')
        self.stdout.write(f'Current Task: {session.current_task[:100] if session.current_task else "None"}')
        
        # Show context information if available
        if session.context:
            context_keys = list(session.context.keys()) if isinstance(session.context, dict) else []
            self.stdout.write(f'Context keys: {context_keys}')
            
            # Check for tool results in context
            if isinstance(session.context, dict) and 'tool_results' in session.context:
                tool_results = session.context['tool_results']
                if isinstance(tool_results, list):
                    self.stdout.write(f'Tool results count: {len(tool_results)}')
                    
                    for i, result in enumerate(tool_results[:5], 1):  # Show first 5 tool results
                        action = result.get('action', {}) if isinstance(result, dict) else {}
                        tool_result = result.get('result', {}) if isinstance(result, dict) else {}
                        
                        tool_name = action.get('action', 'unknown')
                        success = tool_result.get('success', False) if isinstance(tool_result, dict) else False
                        
                        self.stdout.write(f'  {i}. {tool_name}: {"✅" if success else "❌"}')
                        
                        if isinstance(tool_result, dict):
                            if 'error' in tool_result:
                                self.stdout.write(f'     Error: {tool_result["error"]}')
                            if 'results' in tool_result and isinstance(tool_result['results'], list):
                                self.stdout.write(f'     Results: {len(tool_result["results"])} items')
                            if 'base_url' in tool_result:
                                self.stdout.write(f'     Base URL: {tool_result["base_url"]}')
        
        # Show messages from the session
        messages = session.messages.all()
        self.stdout.write(f'Messages: {messages.count()}')
        
        tool_messages = messages.filter(message_type='tool')
        self.stdout.write(f'Tool messages: {tool_messages.count()}')
        
        for i, msg in enumerate(tool_messages[:3], 1):  # Show first 3 tool messages
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                metadata = msg.metadata if isinstance(msg.metadata, dict) else {}
                
                self.stdout.write(f'  Tool Message {i}: {msg.timestamp}')
                if isinstance(content, dict):
                    if 'success' in content:
                        self.stdout.write(f'    Success: {content["success"]}')
                    if 'error' in content:
                        self.stdout.write(f'    Error: {content["error"][:100]}...')
                        
            except Exception as e:
                self.stdout.write(f'  Tool Message {i}: Failed to parse - {e}')

    def extract_and_analyze_urls(self, content):
        self.stdout.write('\nURL ANALYSIS:')
        
        all_urls = set()
        
        # Extract URLs from different content sections
        for field_name, field_content in content.items():
            if isinstance(field_content, str):
                urls = self.extract_urls_from_text(field_content)
                if urls:
                    self.stdout.write(f'  {field_name}: {len(urls)} URLs')
                    all_urls.update(urls)

        if all_urls:
            self.stdout.write(f'Total unique URLs found: {len(all_urls)}')
            for url in sorted(all_urls):
                domain = urlparse(url).netloc
                self.stdout.write(f'  🔗 {url} ({domain})')
        else:
            self.stdout.write('  No URLs found in content')

    def extract_urls_from_text(self, text):
        """Extract URLs from text using regex"""
        url_pattern = r'https?://[^\s\'"<>)}\]]+(?:\.[^\s\'"<>)}\]]+)*/?[^\s\'"<>)}\]]*'
        urls = re.findall(url_pattern, text, re.IGNORECASE)
        
        # Clean up URLs (remove trailing punctuation)
        clean_urls = []
        for url in urls:
            url = url.rstrip('.,;:!?)')
            if url.endswith('"') or url.endswith("'"):
                url = url[:-1]
            clean_urls.append(url)
        
        return clean_urls