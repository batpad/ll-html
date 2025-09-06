from django.core.management.base import BaseCommand
from generator.models import GeneratedPage, GenerationRequest
from agents.models import AgentSession, AgentMessage
import json


class Command(BaseCommand):
    help = 'Inspect a specific generated page with detailed analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            'page_id',
            type=int,
            help='ID of the page to inspect'
        )
        parser.add_argument(
            '--show-content',
            action='store_true',
            help='Show the full HTML content'
        )
        parser.add_argument(
            '--show-agent-session',
            action='store_true',
            help='Show associated agent session details'
        )
        parser.add_argument(
            '--analyze-json-error',
            action='store_true',
            help='Analyze JSON parsing errors in detail'
        )

    def handle(self, *args, **options):
        page_id = options['page_id']
        
        try:
            page = GeneratedPage.objects.get(id=page_id)
        except GeneratedPage.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Page #{page_id} not found'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'INSPECTING PAGE #{page.id}:'))
        self.stdout.write('=' * 60)
        
        # Basic page info
        self.stdout.write(f"Title: {page.title}")
        self.stdout.write(f"Status: {page.status}")
        self.stdout.write(f"Created: {page.created_at}")
        self.stdout.write(f"User Request: {page.user_request}")
        
        if page.error_message:
            self.stdout.write(f"❌ Error: {page.error_message}")
        
        if page.html_content:
            content_length = len(page.html_content)
            self.stdout.write(f"HTML Content: {content_length} characters")
            
            if options['show_content']:
                self.stdout.write("\n📄 FULL HTML CONTENT:")
                self.stdout.write('-' * 40)
                self.stdout.write(page.html_content)
                self.stdout.write('-' * 40)
            else:
                preview = page.html_content[:500] + "..." if len(page.html_content) > 500 else page.html_content
                self.stdout.write(f"Content Preview: {preview}")
        
        # JSON error analysis
        if options['analyze_json_error'] and page.error_message and 'escape' in page.error_message.lower():
            self.analyze_json_error(page)
        
        # Agent session analysis
        if options['show_agent_session']:
            self.analyze_agent_session(page)

    def analyze_json_error(self, page):
        self.stdout.write(f"\n🔍 JSON ERROR ANALYSIS:")
        self.stdout.write('-' * 30)
        
        # Try to find where the JSON parsing failed
        if page.html_content:
            self.stdout.write("Checking HTML content for JSON parsing issues...")
            
            # Look for common problematic patterns
            problematic_patterns = {
                r'\\s\+': 'Regex pattern \\s+ (should be \\\\s\\\\+)',
                r'\\w\+': 'Regex pattern \\w+ (should be \\\\w\\\\+)',  
                r'\\d\+': 'Regex pattern \\d+ (should be \\\\d\\\\+)',
                r'\\n': 'Newline \\n (should be \\\\n)',
                r'\\t': 'Tab \\t (should be \\\\t)',
                r'\\r': 'Carriage return \\r (should be \\\\r)'
            }
            
            for pattern, description in problematic_patterns.items():
                import re
                matches = re.findall(pattern, page.html_content)
                if matches:
                    self.stdout.write(f"⚠️  Found {len(matches)} instances: {description}")
                    # Show first few matches with context
                    for i, match in enumerate(matches[:3]):
                        # Find context around the match
                        match_pos = page.html_content.find(match)
                        start = max(0, match_pos - 50)
                        end = min(len(page.html_content), match_pos + 50)
                        context = page.html_content[start:end]
                        self.stdout.write(f"   Example {i+1}: ...{context}...")
            
            # Try to find the exact character that caused the error
            error_msg = page.error_message
            if 'char' in error_msg and ')' in error_msg:
                try:
                    # Extract character position from error message
                    char_pos_start = error_msg.find('char ') + 5
                    char_pos_end = error_msg.find(')', char_pos_start)
                    char_pos = int(error_msg[char_pos_start:char_pos_end])
                    
                    self.stdout.write(f"\n🎯 ERROR LOCATION (character {char_pos}):")
                    if char_pos < len(page.html_content):
                        start = max(0, char_pos - 100)
                        end = min(len(page.html_content), char_pos + 100)
                        context = page.html_content[start:end]
                        # Highlight the problem character
                        problem_char = page.html_content[char_pos] if char_pos < len(page.html_content) else '?'
                        self.stdout.write(f"Problem character: '{problem_char}' (ASCII {ord(problem_char)})")
                        self.stdout.write(f"Context: ...{context}...")
                        
                        # Show the specific line
                        lines = page.html_content[:char_pos].split('\n')
                        line_num = len(lines)
                        col_num = len(lines[-1]) if lines else 0
                        self.stdout.write(f"Line {line_num}, Column {col_num}")
                except (ValueError, IndexError) as e:
                    self.stdout.write(f"Could not parse error location: {e}")

    def analyze_agent_session(self, page):
        self.stdout.write(f"\n🤖 AGENT SESSION ANALYSIS:")
        self.stdout.write('-' * 30)
        
        # Try to find the associated generation request and agent session
        try:
            # Look for generation requests that might be associated
            gen_requests = GenerationRequest.objects.filter(
                created_at__gte=page.created_at.replace(second=0, microsecond=0),
                created_at__lt=page.created_at.replace(second=59, microsecond=999999)
            ).order_by('created_at')
            
            if gen_requests:
                self.stdout.write(f"Found {gen_requests.count()} potential generation requests:")
                for req in gen_requests:
                    self.stdout.write(f"  Request #{req.id}: {req.model} ({req.created_at})")
            
            # Try to find agent sessions by searching for similar user requests
            if page.user_request:
                search_term = page.user_request[:50]  # First 50 chars
                sessions = AgentSession.objects.filter(
                    current_task__icontains=search_term
                ).order_by('-created_at')[:3]
                
                if sessions:
                    self.stdout.write(f"\nFound {sessions.count()} potential agent sessions:")
                    for session in sessions:
                        self.stdout.write(f"\n  Session: {session.session_id}")
                        self.stdout.write(f"    Task: {session.current_task}")
                        self.stdout.write(f"    Status: {session.task_status}")
                        self.stdout.write(f"    Created: {session.created_at}")
                        
                        # Show tool results
                        tool_results = session.context.get('tool_results', [])
                        self.stdout.write(f"    Tool calls: {len(tool_results)}")
                        
                        successful_tools = sum(1 for tr in tool_results if tr.get('result', {}).get('success', False))
                        self.stdout.write(f"    Successful: {successful_tools}/{len(tool_results)}")
                        
                        # Show messages
                        messages = AgentMessage.objects.filter(session=session).count()
                        self.stdout.write(f"    Messages: {messages}")
                else:
                    self.stdout.write("No matching agent sessions found")
        except Exception as e:
            self.stdout.write(f"Error analyzing agent session: {e}")