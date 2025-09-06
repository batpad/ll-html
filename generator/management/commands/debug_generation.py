from django.core.management.base import BaseCommand
from generator.models import GeneratedPage
from agents.react_agent import ReactAgent
import json
import traceback


class Command(BaseCommand):
    help = 'Debug recent generation failures'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-generation',
            action='store_true',
            help='Test generation with a simple request'
        )
        parser.add_argument(
            '--analyze-recent',
            action='store_true', 
            help='Analyze recent failed generations'
        )

    def handle(self, *args, **options):
        if options['test_generation']:
            self.test_generation()
        
        if options['analyze_recent']:
            self.analyze_recent_failures()

    def test_generation(self):
        self.stdout.write(self.style.SUCCESS('TESTING GENERATION WITH DEBUG:'))
        self.stdout.write('=' * 60)
        
        try:
            agent = ReactAgent()
            result = agent.execute("Create a simple map showing earthquake locations using Montandon data")
            
            self.stdout.write(f"Generation result:")
            self.stdout.write(f"  Success: {result.get('success', False)}")
            
            if result.get('success'):
                html_content = result.get('html_content', {})
                self.stdout.write(f"  Content keys: {list(html_content.keys())}")
                
                # Check for JSON escaping issues
                for key, value in html_content.items():
                    if isinstance(value, str) and ('\\' in value):
                        self.stdout.write(f"  ⚠️  {key} contains backslashes - potential escaping issue")
                        # Show problematic content
                        lines = value.split('\n')
                        for i, line in enumerate(lines[:10], 1):
                            if '\\' in line:
                                self.stdout.write(f"    Line {i}: {line[:100]}...")
                
                # Try to serialize as JSON to catch issues
                try:
                    json_str = json.dumps(html_content)
                    self.stdout.write("  ✅ JSON serialization successful")
                except Exception as e:
                    self.stdout.write(f"  ❌ JSON serialization failed: {e}")
                    
            else:
                error = result.get('error', 'Unknown error')
                self.stdout.write(f"  Error: {error}")
                
        except Exception as e:
            self.stdout.write(f"❌ Generation test failed: {e}")
            traceback.print_exc()

    def analyze_recent_failures(self):
        self.stdout.write(self.style.SUCCESS('ANALYZING RECENT GENERATIONS:'))
        self.stdout.write('=' * 60)
        
        recent_pages = GeneratedPage.objects.all().order_by('-created_at')[:5]
        
        for page in recent_pages:
            self.stdout.write(f"\nPage #{page.id}: {page.title}")
            self.stdout.write(f"  Status: {page.status}")
            self.stdout.write(f"  Created: {page.created_at}")
            
            if page.error_message:
                self.stdout.write(f"  Error: {page.error_message}")
            
            if page.html_content:
                content_length = len(page.html_content)
                self.stdout.write(f"  HTML content: {content_length} characters")
                
                # Check for backslash issues in stored content
                if '\\' in page.html_content:
                    backslash_count = page.html_content.count('\\')
                    self.stdout.write(f"  ⚠️  Contains {backslash_count} backslashes")
                    
                # Try to parse stored content as JSON
                try:
                    if page.html_content.startswith('{'):
                        content_data = json.loads(page.html_content)
                        self.stdout.write(f"  ✅ Stored as valid JSON with keys: {list(content_data.keys())}")
                except Exception as e:
                    self.stdout.write(f"  ❌ JSON parse error: {e}")
            
            self.stdout.write('-' * 40)