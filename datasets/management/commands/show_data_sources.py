from django.core.management.base import BaseCommand
from datasets.models import DataSource
import json


class Command(BaseCommand):
    help = 'Display all configured data sources with their details'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active data sources'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Filter by category (disaster, weather, etc.)'
        )
        parser.add_argument(
            '--show-collections',
            action='store_true',
            help='Show STAC collections for STAC catalogs'
        )
        parser.add_argument(
            '--show-context',
            action='store_true',
            help='Show how data sources appear in agent context'
        )

    def handle(self, *args, **options):
        sources = DataSource.objects.all()
        
        if options['active_only']:
            sources = sources.filter(is_active=True)
            
        if options['category']:
            sources = sources.filter(category=options['category'])
        
        sources = sources.order_by('category', 'name')
        
        if not sources.exists():
            self.stdout.write(self.style.WARNING('No data sources found'))
            return

        if options['show_context']:
            self.show_agent_context(sources)
        else:
            self.show_detailed_sources(sources, options)

    def show_detailed_sources(self, sources, options):
        self.stdout.write(self.style.SUCCESS(f'CONFIGURED DATA SOURCES ({sources.count()} total):'))
        self.stdout.write('=' * 80)
        
        current_category = None
        
        for source in sources:
            if source.category != current_category:
                current_category = source.category
                category_name = dict(source.CATEGORY_CHOICES).get(source.category, source.category)
                self.stdout.write(f'\n{self.style.HTTP_INFO(category_name.upper())}:')
            
            status = "✅ ACTIVE" if source.is_active else "❌ INACTIVE"
            self.stdout.write(f'\n📊 {source.name} ({status})')
            self.stdout.write(f'   Description: {source.description}')
            self.stdout.write(f'   Type: {source.data_type}')
            self.stdout.write(f'   Base URL: {source.base_url}')
            
            if source.is_stac_catalog():
                self.stdout.write(f'   STAC Catalog URL: {source.stac_catalog_url}')
                self.stdout.write(f'   Search URL: {source.get_stac_search_url()}')
                
                if options['show_collections']:
                    collections = source.get_available_collections()
                    self.stdout.write(f'   Collections ({len(collections)}):')
                    for i, coll in enumerate(collections[:10], 1):  # Show first 10
                        self.stdout.write(f'     {i}. {coll}')
                    if len(collections) > 10:
                        self.stdout.write(f'     ... and {len(collections) - 10} more')
                else:
                    collections = source.get_available_collections()
                    self.stdout.write(f'   Collections: {len(collections)} available (use --show-collections to see list)')
            
            if source.llm_context:
                context_preview = source.llm_context[:100] + '...' if len(source.llm_context) > 100 else source.llm_context
                self.stdout.write(f'   LLM Context: {context_preview}')
            
            # Show query patterns if available
            if source.query_patterns:
                patterns = source.query_patterns if isinstance(source.query_patterns, list) else []
                if patterns:
                    # Handle both string and dict patterns
                    pattern_strs = []
                    for pattern in patterns[:3]:
                        if isinstance(pattern, dict):
                            pattern_strs.append(str(pattern))
                        else:
                            pattern_strs.append(str(pattern))
                    self.stdout.write(f'   Query Patterns: {", ".join(pattern_strs)}')
            
            self.stdout.write('-' * 60)

    def show_agent_context(self, sources):
        """Show how data sources appear in the agent context"""
        self.stdout.write(self.style.SUCCESS('AGENT CONTEXT VIEW:'))
        self.stdout.write('=' * 80)
        
        # This mimics the _get_data_sources_context method from ReactAgent
        active_sources = sources.filter(is_active=True).order_by('category', 'name')
        
        if not active_sources.exists():
            self.stdout.write("No configured data sources available.")
            return
        
        context_parts = ["Available Data Sources:"]
        current_category = None
        
        for source in active_sources:
            if source.category != current_category:
                current_category = source.category
                category_name = dict(source.CATEGORY_CHOICES).get(source.category, source.category)
                context_parts.append(f"\n{category_name.upper()}:")
            
            context_parts.append(f"- {source.name}: {source.description}")
            if source.is_stac_catalog():
                collections = source.get_available_collections()[:5]  # First 5 collections
                context_parts.append(f"  Collections: {', '.join(collections)}")
        
        context_text = "\n".join(context_parts)
        self.stdout.write(context_text)
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(f'Total active sources: {active_sources.count()}')
        stac_sources = active_sources.filter(data_type='stac_catalog')
        self.stdout.write(f'STAC catalogs: {stac_sources.count()}')