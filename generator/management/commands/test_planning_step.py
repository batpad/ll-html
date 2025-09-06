from django.core.management.base import BaseCommand
from agents.react_agent import ReactAgent
import json


class Command(BaseCommand):
    help = 'Test the new planning step in the React agent'

    def add_arguments(self, parser):
        parser.add_argument(
            '--request',
            type=str,
            default="Create a dashboard showing recent wildfire activity with evacuation zones",
            help='User request to test'
        )
        parser.add_argument(
            '--show-plan',
            action='store_true',
            help='Show the generated implementation plan'
        )
        parser.add_argument(
            '--show-research',
            action='store_true', 
            help='Show research phase details'
        )

    def handle(self, *args, **options):
        test_request = options['request']
        
        self.stdout.write(self.style.SUCCESS('TESTING PLANNING STEP:'))
        self.stdout.write('=' * 60)
        self.stdout.write(f"Test Request: {test_request}")
        self.stdout.write()
        
        try:
            # Create agent and execute with planning
            agent = ReactAgent()
            
            # Test just the planning step first
            self.stdout.write("🎯 STEP 1: Creating Implementation Plan...")
            planning_result = agent._create_implementation_plan()
            agent.context['user_request'] = test_request
            
            if planning_result.get('success'):
                plan = planning_result['plan']
                self.stdout.write("✅ Planning step successful!")
                
                if options['show_plan']:
                    self.stdout.write("\n📋 GENERATED PLAN:")
                    self.stdout.write(f"   Summary: {plan.get('summary', 'N/A')}")
                    self.stdout.write(f"   User Intent: {plan.get('user_intent', 'N/A')}")
                    
                    requirements = plan.get('functional_requirements', [])
                    if requirements:
                        self.stdout.write("   Functional Requirements:")
                        for req in requirements:
                            self.stdout.write(f"     - {req}")
                    
                    data_reqs = plan.get('data_requirements', [])
                    if data_reqs:
                        self.stdout.write("   Data Requirements:")
                        for req in data_reqs:
                            self.stdout.write(f"     - {req}")
                    
                    ui_components = plan.get('ui_components', [])
                    if ui_components:
                        self.stdout.write("   UI Components:")
                        for comp in ui_components:
                            self.stdout.write(f"     - {comp}")
                    
                    research_tasks = plan.get('research_tasks', [])
                    if research_tasks:
                        self.stdout.write("   Research Tasks:")
                        for task in research_tasks:
                            self.stdout.write(f"     - {task}")
                
                # Test full execution if requested
                if options['show_research']:
                    self.stdout.write("\n🔍 STEP 2: Testing Full Execution with Research...")
                    agent_full = ReactAgent()
                    result = agent_full.execute(test_request)
                    
                    if result.get('success'):
                        self.stdout.write("✅ Full execution successful!")
                        
                        # Show research phase details
                        context = agent_full.context
                        tool_results = context.get('tool_results', [])
                        self.stdout.write(f"   Tool calls made: {len(tool_results)}")
                        
                        successful_tools = sum(1 for tr in tool_results if tr.get('result', {}).get('success', False))
                        self.stdout.write(f"   Successful tools: {successful_tools}/{len(tool_results)}")
                        
                        # Show which research tasks were completed
                        plan_tasks = plan.get('research_tasks', [])
                        self.stdout.write(f"   Planned research tasks: {len(plan_tasks)}")
                        
                        html_content = result.get('html_content', {})
                        if html_content:
                            title = html_content.get('title', 'No title')
                            self.stdout.write(f"   Generated: {title}")
                    else:
                        error = result.get('error', 'Unknown error')
                        self.stdout.write(f"❌ Full execution failed: {error}")
            else:
                error = planning_result.get('error', 'Unknown error')
                self.stdout.write(f"❌ Planning step failed: {error}")
                
        except Exception as e:
            self.stdout.write(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Test completed!")