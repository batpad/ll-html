from django.core.management.base import BaseCommand
from generator.models import HTMLTemplate


class Command(BaseCommand):
    help = 'Inspect HTML templates and their structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--template-id',
            type=int,
            help='Specific template ID to inspect'
        )
        parser.add_argument(
            '--template-name',
            type=str,
            help='Specific template name to inspect'
        )
        parser.add_argument(
            '--template-type',
            type=str,
            help='Filter by template type (dashboard, map, generic)'
        )
        parser.add_argument(
            '--show-content',
            action='store_true',
            help='Show full template content'
        )
        parser.add_argument(
            '--show-css',
            action='store_true',
            help='Show CSS template content'
        )
        parser.add_argument(
            '--show-js',
            action='store_true',
            help='Show JavaScript template content'
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active templates'
        )

    def handle(self, *args, **options):
        # Build query
        queryset = HTMLTemplate.objects.all()
        
        if options['active_only']:
            queryset = queryset.filter(is_active=True)
        
        if options['template_id']:
            queryset = queryset.filter(id=options['template_id'])
        
        if options['template_name']:
            queryset = queryset.filter(name__icontains=options['template_name'])
        
        if options['template_type']:
            queryset = queryset.filter(template_type=options['template_type'])
        
        templates = queryset.order_by('template_type', 'name')
        
        if not templates.exists():
            self.stdout.write(self.style.WARNING('No templates found matching criteria'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'FOUND {templates.count()} TEMPLATES:'))
        self.stdout.write('=' * 70)
        
        for template in templates:
            self.show_template_info(template, options)
            self.stdout.write('-' * 70)

    def show_template_info(self, template, options):
        status_icon = "✅" if template.is_active else "❌"
        self.stdout.write(f"\n{status_icon} {template.name} (ID: {template.id})")
        self.stdout.write(f"   Type: {template.template_type}")
        self.stdout.write(f"   Description: {template.description}")
        self.stdout.write(f"   Created: {template.created_at}")
        
        # Show required libraries
        libraries = template.required_libraries.all()
        if libraries.exists():
            self.stdout.write(f"   Libraries ({libraries.count()}):")
            for lib in libraries:
                self.stdout.write(f"     - {lib.name} ({lib.library_type}): {lib.url}")
        
        # Show content lengths
        template_content_len = len(template.template_content or '')
        css_content_len = len(template.css_template or '')
        js_content_len = len(template.js_template or '')
        
        self.stdout.write(f"   Content sizes:")
        self.stdout.write(f"     HTML template: {template_content_len} chars")
        self.stdout.write(f"     CSS template: {css_content_len} chars")
        self.stdout.write(f"     JS template: {js_content_len} chars")
        
        # Show full content if requested
        if options['show_content']:
            self.stdout.write(f"\n📄 HTML TEMPLATE CONTENT:")
            self.stdout.write(template.template_content or 'No content')
        
        if options['show_css']:
            self.stdout.write(f"\n🎨 CSS TEMPLATE CONTENT:")
            self.stdout.write(template.css_template or 'No CSS content')
        
        if options['show_js']:
            self.stdout.write(f"\n🔧 JAVASCRIPT TEMPLATE CONTENT:")
            self.stdout.write(template.js_template or 'No JavaScript content')
        
        # Show preview if not showing full content
        if not options['show_content'] and template.template_content:
            preview = template.template_content[:300] + "..." if len(template.template_content) > 300 else template.template_content
            self.stdout.write(f"\n   Preview: {preview}")
        
        # Show where placeholders are
        if template.template_content:
            placeholders = []
            content = template.template_content
            
            # Common placeholder patterns
            placeholder_patterns = [
                '{{ main_content }}',
                '{{ custom_css }}', 
                '{{ custom_js }}',
                '{{ title }}',
                '{{ description }}',
                '{%', '{{', '%}', '}}'
            ]
            
            for pattern in placeholder_patterns:
                if pattern in content:
                    placeholders.append(pattern)
            
            if placeholders:
                self.stdout.write(f"   🎯 Placeholders found: {', '.join(placeholders)}")

    def show_injection_analysis(self, template):
        """Analyze how content gets injected into the template"""
        self.stdout.write(f"\n🔍 INJECTION ANALYSIS:")
        
        content = template.template_content or ''
        
        # Check if template has full HTML structure
        has_html_tag = '<html' in content.lower()
        has_head_tag = '<head' in content.lower()
        has_body_tag = '<body' in content.lower()
        
        self.stdout.write(f"   Has <html> tag: {'Yes' if has_html_tag else 'No'}")
        self.stdout.write(f"   Has <head> tag: {'Yes' if has_head_tag else 'No'}")
        self.stdout.write(f"   Has <body> tag: {'Yes' if has_body_tag else 'No'}")
        
        # Look for main content injection point
        if '{{ main_content }}' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if '{{ main_content }}' in line:
                    self.stdout.write(f"   Main content injected at line {i}: {line.strip()}")
                    
                    # Show surrounding context
                    start = max(0, i-3)
                    end = min(len(lines), i+2)
                    self.stdout.write(f"   Context (lines {start+1}-{end}):")
                    for j in range(start, end):
                        marker = ">>> " if j == i-1 else "    "
                        self.stdout.write(f"   {marker}{j+1:2}: {lines[j]}")
        else:
            self.stdout.write("   ⚠️  No {{ main_content }} placeholder found!")