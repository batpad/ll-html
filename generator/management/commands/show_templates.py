from django.core.management.base import BaseCommand
from generator.models import HTMLTemplate
import json


class Command(BaseCommand):
    help = 'Display all HTML templates with their details'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active templates'
        )
        parser.add_argument(
            '--template-type',
            type=str,
            help='Filter by template type (map, dashboard, etc.)'
        )
        parser.add_argument(
            '--show-content',
            action='store_true',
            help='Show template content preview'
        )
        parser.add_argument(
            '--show-libraries',
            action='store_true',
            help='Show required libraries in detail'
        )

    def handle(self, *args, **options):
        templates = HTMLTemplate.objects.all()
        
        if options['active_only']:
            templates = templates.filter(is_active=True)
            
        if options['template_type']:
            templates = templates.filter(template_type=options['template_type'])
        
        templates = templates.order_by('template_type', 'name')
        
        if not templates.exists():
            self.stdout.write(self.style.WARNING('No HTML templates found'))
            return

        self.show_templates(templates, options)

    def show_templates(self, templates, options):
        self.stdout.write(self.style.SUCCESS(f'HTML TEMPLATES ({templates.count()} total):'))
        self.stdout.write('=' * 80)
        
        current_type = None
        
        for template in templates:
            if template.template_type != current_type:
                current_type = template.template_type
                type_name = dict(template.TEMPLATE_TYPES).get(template.template_type, template.template_type)
                self.stdout.write(f'\n{self.style.HTTP_INFO(type_name.upper())}:')
            
            status = "✅ ACTIVE" if template.is_active else "❌ INACTIVE"
            self.stdout.write(f'\n📄 {template.name} ({status})')
            self.stdout.write(f'   Description: {template.description}')
            self.stdout.write(f'   Created: {template.created_at}')
            
            # Show required libraries
            if template.required_libraries:
                libraries = template.required_libraries
                if isinstance(libraries, list) and libraries:
                    self.stdout.write(f'   📚 Required Libraries ({len(libraries)}):')
                    if options['show_libraries']:
                        for i, lib in enumerate(libraries, 1):
                            if isinstance(lib, dict):
                                name = lib.get('name', 'Unknown')
                                url = lib.get('url', 'No URL')
                                self.stdout.write(f'     {i}. {name}: {url}')
                            else:
                                self.stdout.write(f'     {i}. {lib}')
                    else:
                        lib_names = []
                        for lib in libraries:
                            if isinstance(lib, dict):
                                lib_names.append(lib.get('name', 'Unknown'))
                            else:
                                lib_names.append(str(lib))
                        self.stdout.write(f'     {", ".join(lib_names[:5])}')
                        if len(libraries) > 5:
                            self.stdout.write(f'     ... and {len(libraries) - 5} more')
            else:
                self.stdout.write(f'   📚 Required Libraries: None')
            
            # Show content preview
            if options['show_content']:
                if template.template_content:
                    content_preview = template.template_content[:200].replace('\n', ' ')
                    self.stdout.write(f'   📝 Content Preview: {content_preview}...')
                
                if template.css_template:
                    css_preview = template.css_template[:100].replace('\n', ' ')
                    self.stdout.write(f'   🎨 CSS Template: {css_preview}...')
                
                if template.js_template:
                    js_preview = template.js_template[:100].replace('\n', ' ')
                    self.stdout.write(f'   ⚡ JS Template: {js_preview}...')
            
            self.stdout.write('-' * 60)

        # Summary
        self.stdout.write(f'\n{self.style.SUCCESS("SUMMARY:")}')
        by_type = {}
        for template in templates:
            type_name = dict(template.TEMPLATE_TYPES).get(template.template_type, template.template_type)
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        for template_type, count in by_type.items():
            self.stdout.write(f'  {template_type}: {count} templates')
        
        active_count = templates.filter(is_active=True).count()
        self.stdout.write(f'  Active: {active_count}/{templates.count()}')