from django.core.management.base import BaseCommand
from generator.models import GeneratedPage, GenerationRequest
from agents.models import AgentSession, AgentMessage
import json
import re
from collections import Counter


class Command(BaseCommand):
    help = 'Deep analysis of generation failures and patterns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of recent generations to analyze'
        )
        parser.add_argument(
            '--show-prompts',
            action='store_true',
            help='Show the actual prompts sent to LLM'
        )
        parser.add_argument(
            '--json-issues',
            action='store_true',
            help='Focus on JSON parsing issues'
        )
        parser.add_argument(
            '--tool-failures',
            action='store_true',
            help='Analyze tool execution failures'
        )

    def handle(self, *args, **options):
        if options['json_issues']:
            self.analyze_json_issues(options['count'])
        elif options['tool_failures']:
            self.analyze_tool_failures(options['count'])
        elif options['show_prompts']:
            self.analyze_prompts(options['count'])
        else:
            self.comprehensive_analysis(options['count'])

    def comprehensive_analysis(self, count):
        self.stdout.write(self.style.SUCCESS(f'COMPREHENSIVE FAILURE ANALYSIS ({count} recent generations):'))
        self.stdout.write('=' * 80)
        
        pages = GeneratedPage.objects.all().order_by('-created_at')[:count]
        
        success_count = 0
        failure_count = 0
        json_error_count = 0
        tool_error_count = 0
        
        for page in pages:
            if page.status == 'completed':
                success_count += 1
            else:
                failure_count += 1
                if page.error_message and ('escape' in page.error_message.lower() or 'json' in page.error_message.lower()):
                    json_error_count += 1
        
        self.stdout.write(f"\n📊 SUMMARY:")
        self.stdout.write(f"  ✅ Successful: {success_count}")
        self.stdout.write(f"  ❌ Failed: {failure_count}")
        self.stdout.write(f"  🔧 JSON errors: {json_error_count}")
        self.stdout.write(f"  Success rate: {success_count/(success_count+failure_count)*100:.1f}%")
        
        # Analyze user request patterns
        self.stdout.write(f"\n📝 USER REQUEST PATTERNS:")
        request_lengths = [len(page.user_request or '') for page in pages if page.user_request]
        if request_lengths:
            avg_length = sum(request_lengths) / len(request_lengths)
            self.stdout.write(f"  Average request length: {avg_length:.0f} characters")
            
        # Show detailed failures
        self.stdout.write(f"\n❌ DETAILED FAILURES:")
        failures = [p for p in pages if p.status == 'failed']
        for page in failures[:5]:
            self.stdout.write(f"\n  Page #{page.id}: {page.title}")
            self.stdout.write(f"    Request: {(page.user_request or '')[:100]}...")
            self.stdout.write(f"    Error: {page.error_message}")
            
            # Try to find associated agent session
            try:
                gen_request = page.generationrequest_set.first()
                if gen_request:
                    agent_sessions = AgentSession.objects.filter(
                        context__user_request__icontains=(page.user_request or '')[:50]
                    ).order_by('-created_at')[:1]
                    
                    if agent_sessions:
                        session = agent_sessions[0]
                        tool_results = session.context.get('tool_results', [])
                        self.stdout.write(f"    Tools used: {len(tool_results)}")
                        
                        # Count successful vs failed tools
                        successful_tools = sum(1 for tr in tool_results if tr.get('result', {}).get('success', False))
                        self.stdout.write(f"    Successful tool calls: {successful_tools}/{len(tool_results)}")
                        
            except Exception as e:
                self.stdout.write(f"    Could not analyze agent session: {e}")

    def analyze_json_issues(self, count):
        self.stdout.write(self.style.SUCCESS(f'JSON PARSING ISSUES ANALYSIS:'))
        self.stdout.write('=' * 60)
        
        pages = GeneratedPage.objects.all().order_by('-created_at')[:count]
        json_failures = [p for p in pages if p.error_message and 'escape' in p.error_message.lower()]
        
        self.stdout.write(f"Found {len(json_failures)} JSON-related failures out of {count} recent generations")
        
        for page in json_failures:
            self.stdout.write(f"\n❌ Page #{page.id}: {page.title}")
            self.stdout.write(f"   Error: {page.error_message}")
            
            # Try to find the agent session and LLM responses
            try:
                gen_request = page.generationrequest_set.first()
                if gen_request and hasattr(gen_request, 'session_id'):
                    messages = AgentMessage.objects.filter(
                        session__session_id=gen_request.session_id,
                        message_type='llm_response'
                    ).order_by('-created_at')[:3]
                    
                    for msg in messages:
                        content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                        
                        # Look for problematic patterns
                        backslash_count = content.count('\\')
                        if backslash_count > 0:
                            self.stdout.write(f"   🔍 Found {backslash_count} backslashes in LLM response")
                            
                        # Check for common problematic patterns
                        problematic_patterns = [
                            r'\\s\+', r'\\w\+', r'\\d\+', r'\\n', r'\\t'
                        ]
                        
                        for pattern in problematic_patterns:
                            matches = len(re.findall(pattern, content))
                            if matches > 0:
                                self.stdout.write(f"   ⚠️  Found {matches} instances of pattern: {pattern}")
            except Exception as e:
                self.stdout.write(f"   Could not analyze LLM responses: {e}")

    def analyze_tool_failures(self, count):
        self.stdout.write(self.style.SUCCESS(f'TOOL EXECUTION FAILURES ANALYSIS:'))
        self.stdout.write('=' * 60)
        
        # Get recent agent sessions
        sessions = AgentSession.objects.all().order_by('-created_at')[:count]
        
        tool_error_patterns = Counter()
        tool_success_rates = Counter()
        
        for session in sessions:
            tool_results = session.context.get('tool_results', [])
            
            for tool_result in tool_results:
                action = tool_result.get('action', {})
                result = tool_result.get('result', {})
                tool_name = action.get('action', 'unknown')
                
                # Track success rates
                if result.get('success', False):
                    tool_success_rates[f"{tool_name}_success"] += 1
                else:
                    tool_success_rates[f"{tool_name}_failure"] += 1
                    error = result.get('error', 'Unknown error')
                    tool_error_patterns[f"{tool_name}: {error[:50]}"] += 1
        
        self.stdout.write("\n📊 TOOL SUCCESS RATES:")
        tools = set()
        for key in tool_success_rates.keys():
            tool = key.replace('_success', '').replace('_failure', '')
            tools.add(tool)
        
        for tool in tools:
            successes = tool_success_rates.get(f"{tool}_success", 0)
            failures = tool_success_rates.get(f"{tool}_failure", 0)
            total = successes + failures
            if total > 0:
                rate = successes / total * 100
                self.stdout.write(f"  {tool}: {rate:.1f}% ({successes}/{total})")
        
        self.stdout.write("\n❌ COMMON TOOL ERRORS:")
        for error, count in tool_error_patterns.most_common(10):
            self.stdout.write(f"  {count}x: {error}")

    def analyze_prompts(self, count):
        self.stdout.write(self.style.SUCCESS(f'PROMPT ANALYSIS:'))
        self.stdout.write('=' * 60)
        
        # Look at recent agent messages for prompt patterns
        sessions = AgentSession.objects.all().order_by('-created_at')[:count]
        
        for session in sessions[:3]:  # Show detail for top 3
            self.stdout.write(f"\n🔍 Session: {session.session_id}")
            self.stdout.write(f"   Task: {session.current_task[:100]}...")
            self.stdout.write(f"   Status: {session.task_status}")
            
            # Get LLM messages for this session
            messages = AgentMessage.objects.filter(
                session=session,
                message_type__in=['llm_request', 'llm_response']
            ).order_by('created_at')
            
            self.stdout.write(f"   Messages: {messages.count()}")
            
            for msg in messages[:2]:  # Show first 2 messages
                msg_type = "🤖 REQUEST" if msg.message_type == 'llm_request' else "💭 RESPONSE"
                content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                self.stdout.write(f"   {msg_type}: {content_preview}")