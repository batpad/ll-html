from django.core.management.base import BaseCommand
from agents.models import AgentSession, AgentMessage
import json
import re


class Command(BaseCommand):
    help = 'Inspect agent session with detailed LLM message analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            'session_id',
            type=str,
            help='Session ID to inspect'
        )
        parser.add_argument(
            '--show-messages',
            action='store_true',
            help='Show all messages in the session'
        )
        parser.add_argument(
            '--show-llm-responses',
            action='store_true',
            help='Show LLM responses with JSON analysis'
        )
        parser.add_argument(
            '--show-tool-results',
            action='store_true',
            help='Show detailed tool execution results'
        )
        parser.add_argument(
            '--analyze-json-issues',
            action='store_true',
            help='Analyze JSON parsing issues in LLM responses'
        )

    def handle(self, *args, **options):
        session_id = options['session_id']
        
        try:
            session = AgentSession.objects.get(session_id=session_id)
        except AgentSession.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Session {session_id} not found'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'INSPECTING AGENT SESSION: {session_id}'))
        self.stdout.write('=' * 70)
        
        # Basic session info
        self.stdout.write(f"Task: {session.current_task}")
        self.stdout.write(f"Status: {session.task_status}")
        self.stdout.write(f"Created: {session.created_at}")
        self.stdout.write(f"Updated: {session.updated_at}")
        
        # Context analysis
        context = session.context or {}
        self.stdout.write(f"\n📊 CONTEXT SUMMARY:")
        self.stdout.write(f"  Keys: {list(context.keys())}")
        
        tool_results = context.get('tool_results', [])
        self.stdout.write(f"  Tool results: {len(tool_results)}")
        
        successful_tools = sum(1 for tr in tool_results if tr.get('result', {}).get('success', False))
        self.stdout.write(f"  Successful tools: {successful_tools}/{len(tool_results)}")
        
        reasoning_steps = context.get('reasoning_steps', [])
        self.stdout.write(f"  Reasoning steps: {len(reasoning_steps)}")
        
        # Messages analysis
        messages = AgentMessage.objects.filter(session=session).order_by('timestamp')
        self.stdout.write(f"\n📬 MESSAGES: {messages.count()} total")
        
        message_types = {}
        for msg in messages:
            message_types[msg.message_type] = message_types.get(msg.message_type, 0) + 1
        
        for msg_type, count in message_types.items():
            self.stdout.write(f"  {msg_type}: {count}")
        
        if options['show_tool_results']:
            self.show_tool_results(context.get('tool_results', []))
        
        if options['show_llm_responses'] or options['analyze_json_issues']:
            self.analyze_llm_responses(session, options['analyze_json_issues'])
        
        if options['show_messages']:
            self.show_all_messages(messages)

    def show_tool_results(self, tool_results):
        self.stdout.write(f"\n🔧 DETAILED TOOL RESULTS:")
        self.stdout.write('-' * 40)
        
        for i, tool_result in enumerate(tool_results, 1):
            action = tool_result.get('action', {})
            result = tool_result.get('result', {})
            timestamp = tool_result.get('timestamp', 'Unknown')
            
            tool_name = action.get('action', 'Unknown')
            parameters = action.get('parameters', {})
            
            status = "✅" if result.get('success', False) else "❌"
            self.stdout.write(f"\n{i}. {status} {tool_name} ({timestamp})")
            
            # Show parameters
            if parameters:
                if isinstance(parameters, dict):
                    param_summary = []
                    for key, value in parameters.items():
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:47] + "..."
                        param_summary.append(f"{key}={value}")
                    self.stdout.write(f"   Params: {', '.join(param_summary)}")
                else:
                    param_str = str(parameters)[:100] + "..." if len(str(parameters)) > 100 else str(parameters)
                    self.stdout.write(f"   Params: {param_str}")
            
            # Show result summary
            if result.get('success'):
                if 'results' in result and isinstance(result['results'], list):
                    self.stdout.write(f"   Result: Found {len(result['results'])} items")
                elif 'sample_features' in result:
                    total = result.get('total_found', 0)
                    props = len(result.get('available_properties', []))
                    self.stdout.write(f"   Result: {total} features with {props} properties")
                elif 'is_accessible' in result:
                    status_code = result.get('status_code', 'unknown')
                    accessible = result.get('is_accessible', False)
                    self.stdout.write(f"   Result: API {'accessible' if accessible else 'not accessible'} (status: {status_code})")
                else:
                    self.stdout.write(f"   Result: Success (keys: {list(result.keys())})")
            else:
                error = result.get('error', 'Unknown error')
                self.stdout.write(f"   Error: {error}")

    def analyze_llm_responses(self, session, analyze_json_issues):
        self.stdout.write(f"\n🤖 LLM RESPONSES ANALYSIS:")
        self.stdout.write('-' * 40)
        
        # Get LLM responses in chronological order
        llm_responses = AgentMessage.objects.filter(
            session=session,
            message_type='llm_response'
        ).order_by('timestamp')
        
        self.stdout.write(f"Found {llm_responses.count()} LLM responses")
        
        for i, response in enumerate(llm_responses, 1):
            self.stdout.write(f"\n🔍 Response {i} ({response.timestamp}):")
            self.stdout.write(f"   Length: {len(response.content)} characters")
            
            # Show preview
            preview = response.content[:200] + "..." if len(response.content) > 200 else response.content
            self.stdout.write(f"   Preview: {preview}")
            
            if analyze_json_issues:
                self.analyze_json_in_response(response.content, i)

    def analyze_json_in_response(self, content, response_num):
        self.stdout.write(f"\n   🔍 JSON Analysis for Response {response_num}:")
        
        # Count backslashes
        single_backslash_count = 0
        double_backslash_count = 0
        
        i = 0
        while i < len(content):
            if content[i] == '\\':
                if i + 1 < len(content) and content[i + 1] == '\\':
                    double_backslash_count += 1
                    i += 2  # Skip both backslashes
                else:
                    single_backslash_count += 1
                    i += 1
            else:
                i += 1
        
        self.stdout.write(f"   Single backslashes: {single_backslash_count}")
        self.stdout.write(f"   Double backslashes: {double_backslash_count}")
        
        # Look for common problematic patterns
        problematic_patterns = {
            r'(?<!\\)\\s\+': 'Unescaped regex \\s+',
            r'(?<!\\)\\w\+': 'Unescaped regex \\w+',
            r'(?<!\\)\\d\+': 'Unescaped regex \\d+',
            r'(?<!\\)\\n(?!")': 'Unescaped \\n',
            r'(?<!\\)\\t(?!")': 'Unescaped \\t',
            r'(?<!\\)\\r(?!")': 'Unescaped \\r'
        }
        
        for pattern, description in problematic_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                self.stdout.write(f"   ⚠️  {description}: {len(matches)} instances")
                # Show first match with context
                match = matches[0]
                match_pos = content.find(match)
                if match_pos != -1:
                    start = max(0, match_pos - 30)
                    end = min(len(content), match_pos + 30)
                    context_str = content[start:end].replace('\n', '\\n')
                    self.stdout.write(f"      Example: ...{context_str}...")
        
        # Try to parse as JSON
        try:
            # First try direct parsing
            json.loads(content)
            self.stdout.write(f"   ✅ Valid JSON")
        except json.JSONDecodeError as e:
            self.stdout.write(f"   ❌ JSON Error: {e}")
            
            # Try to find the error location
            if hasattr(e, 'pos'):
                error_pos = e.pos
                start = max(0, error_pos - 50)
                end = min(len(content), error_pos + 50)
                error_context = content[start:end].replace('\n', '\\n')
                self.stdout.write(f"      Error context: ...{error_context}...")
                
                if error_pos < len(content):
                    error_char = content[error_pos]
                    self.stdout.write(f"      Error character: '{error_char}' (ASCII {ord(error_char)})")
        
        # Check if it's wrapped in markdown
        if content.strip().startswith('```json') or content.strip().startswith('```'):
            self.stdout.write(f"   📝 Content wrapped in markdown - this might need cleaning")

    def show_all_messages(self, messages):
        self.stdout.write(f"\n📬 ALL MESSAGES:")
        self.stdout.write('-' * 40)
        
        for i, message in enumerate(messages, 1):
            msg_type_icon = {
                'user': '👤',
                'agent': '🤖',
                'tool': '🔧',
                'llm_request': '📤',
                'llm_response': '📥',
                'system': '⚙️'
            }.get(message.message_type, '❓')
            
            self.stdout.write(f"\n{i}. {msg_type_icon} {message.message_type} ({message.timestamp})")
            
            # Show content preview
            content_preview = message.content[:150] + "..." if len(message.content) > 150 else message.content
            content_preview = content_preview.replace('\n', '\\n')
            self.stdout.write(f"   {content_preview}")
            
            # Show metadata if present
            if message.metadata:
                metadata_str = str(message.metadata)[:100] + "..." if len(str(message.metadata)) > 100 else str(message.metadata)
                self.stdout.write(f"   Metadata: {metadata_str}")