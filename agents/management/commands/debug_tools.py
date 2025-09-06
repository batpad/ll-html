from django.core.management.base import BaseCommand
from agents.tools import tool_registry
from agents.models import AgentSession
import json


class Command(BaseCommand):
    help = 'Debug agent tools and sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-tools',
            action='store_true',
            help='Test all available tools with sample data'
        )
        parser.add_argument(
            '--session-id',
            type=str,
            help='Debug specific agent session'
        )

    def handle(self, *args, **options):
        if options['test_tools']:
            self.test_tools()
        
        if options['session_id']:
            self.debug_session(options['session_id'])
        
        if not options['test_tools'] and not options['session_id']:
            self.show_available_tools()
            self.show_recent_sessions()

    def show_available_tools(self):
        self.stdout.write(self.style.SUCCESS('AVAILABLE TOOLS:'))
        self.stdout.write('=' * 50)
        
        tools = tool_registry.get_available_tools()
        for tool_name, tool_class in tools.items():
            self.stdout.write(f'{tool_name}: {tool_class.description}')
        
        self.stdout.write(f'\nTotal tools available: {len(tools)}')

    def show_recent_sessions(self):
        self.stdout.write('\n' + self.style.SUCCESS('RECENT AGENT SESSIONS:'))
        self.stdout.write('=' * 50)
        
        sessions = AgentSession.objects.all().order_by('-created_at')[:5]
        for session in sessions:
            self.stdout.write(f'Session: {session.session_id}')
            self.stdout.write(f'  Status: {session.task_status}')
            self.stdout.write(f'  Created: {session.created_at}')
            self.stdout.write(f'  Context keys: {list(session.context.keys()) if session.context else []}')
            
            if session.context and 'tool_results' in session.context:
                tool_results = session.context.get('tool_results', [])
                self.stdout.write(f'  Tool results: {len(tool_results)}')
                for i, result in enumerate(tool_results[:3], 1):
                    action = result.get('action', {})
                    self.stdout.write(f'    {i}. {action.get("action", "unknown")}')
            
            self.stdout.write('-' * 30)

    def test_tools(self):
        self.stdout.write(self.style.SUCCESS('TESTING TOOLS:'))
        self.stdout.write('=' * 50)
        
        tools = tool_registry.get_available_tools()
        
        # Test each tool with safe parameters
        test_params = {
            'web_search': {
                'query': 'earthquake data API',
                'limit': 2
            },
            'validate_api_endpoint': {
                'url': 'https://httpbin.org/get'
            },
            'fetch_stac_sample_data': {
                'collection': 'gdacs-events',
                'limit': 2
            },
            'validate_html_endpoints': {
                'html_content': '<html><script>fetch("https://httpbin.org/get")</script></html>'
            }
        }
        
        for tool_name, tool_class in tools.items():
            self.stdout.write(f'\nTesting {tool_name}...')
            
            if tool_name in test_params:
                try:
                    result = tool_class.execute(**test_params[tool_name])  # Unpack parameters
                    success = result.get('success', False) if isinstance(result, dict) else False
                    self.stdout.write(f'  Result: {"✅ Success" if success else "❌ Failed"}')
                    
                    if success and isinstance(result, dict):
                        # Show some success details
                        if 'total_found' in result:
                            self.stdout.write(f'  Found: {result["total_found"]} items')
                        if 'endpoints' in result and isinstance(result['endpoints'], list):
                            self.stdout.write(f'  Endpoints found: {len(result["endpoints"])}')
                    
                    if not success and isinstance(result, dict):
                        error = result.get('error', 'Unknown error')
                        self.stdout.write(f'  Error: {error[:100]}...')
                        
                except Exception as e:
                    self.stdout.write(f'  Exception: {e}')
            else:
                self.stdout.write(f'  Skipped: No test parameters defined')

    def debug_session(self, session_id):
        self.stdout.write(self.style.SUCCESS(f'DEBUGGING SESSION: {session_id}'))
        self.stdout.write('=' * 50)
        
        try:
            session = AgentSession.objects.get(session_id=session_id)
            
            self.stdout.write(f'Status: {session.task_status}')
            self.stdout.write(f'Created: {session.created_at}')
            self.stdout.write(f'Updated: {session.updated_at}')
            self.stdout.write(f'Current task: {session.current_task}')
            
            self.stdout.write('\nCONTEXT:')
            if session.context:
                for key, value in session.context.items():
                    if key == 'tool_results' and isinstance(value, list):
                        self.stdout.write(f'  {key}: {len(value)} results')
                        for i, result in enumerate(value, 1):
                            action = result.get('action', {})
                            tool_result = result.get('result', {})
                            success = tool_result.get('success', False) if isinstance(tool_result, dict) else False
                            
                            self.stdout.write(f'    {i}. {action.get("action", "unknown")}: {"✅" if success else "❌"}')
                            if not success and isinstance(tool_result, dict):
                                error = tool_result.get('error', 'No error message')
                                self.stdout.write(f'       Error: {error[:100]}...')
                    else:
                        value_str = str(value)[:100] if not isinstance(value, (dict, list)) else f'{type(value).__name__} with {len(value)} items'
                        self.stdout.write(f'  {key}: {value_str}')
            else:
                self.stdout.write('  No context found')
            
            # Show messages
            messages = session.messages.all()
            self.stdout.write(f'\nMESSAGES: {messages.count()}')
            for msg in messages:
                self.stdout.write(f'  {msg.timestamp}: {msg.message_type} - {msg.content[:100]}...')
                
        except AgentSession.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Session {session_id} not found'))