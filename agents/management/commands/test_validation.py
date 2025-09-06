from django.core.management.base import BaseCommand
from agents.validation_tools import ValidationOrchestrator
from agents.validation_agent import ValidationAgent
import json


class Command(BaseCommand):
    help = 'Test the validation system with sample content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['validation', 'fixing', 'both'],
            default='both',
            help='Type of test to run'
        )

    def handle(self, *args, **options):
        if options['test_type'] in ['validation', 'both']:
            self.test_validation()
        
        if options['test_type'] in ['fixing', 'both']:
            self.test_validation_and_fixing()

    def test_validation(self):
        self.stdout.write(self.style.SUCCESS('TESTING VALIDATION TOOLS:'))
        self.stdout.write('=' * 60)

        # Test with problematic content
        problematic_content = {
            "title": "Test Page",
            "description": "A test page with issues",
            "main_content": """
                <div class="container">
                    <h1>Test Map</h1>
                    <div class="row">
                        <div class="col-8">
                            <!-- Missing div with id="map" for Leaflet -->
                        </div>
                        <div class="col-4">
                            <canvas></canvas> <!-- Missing id for Chart.js -->
                        </div>
                    </div>
                </div>
            """,
            "custom_css": """
                .map-style { height: 400px; }
            """,
            "custom_js": """
                // This will fail - no element with id 'map'
                const map = L.map('map').setView([0, 0], 2);
                
                // This will fail - no canvas element with id 'myChart'
                const ctx = document.getElementById('myChart').getContext('2d');
                const chart = new Chart(ctx, {
                    type: 'line',
                    data: { labels: [], datasets: [] }
                }
                // Missing closing brace and semicolon
            """
        }

        # Run validation
        validator = ValidationOrchestrator()
        result = validator.validate_generated_content(problematic_content)

        self.stdout.write(f"Validation completed:")
        self.stdout.write(f"  Total issues: {result['total_issues']}")
        self.stdout.write(f"  Severity: {result['overall_severity']}")
        self.stdout.write(f"  Needs fixing: {result['needs_fixing']}")
        
        if result['issues']:
            self.stdout.write("\nIssues found:")
            for i, issue in enumerate(result['issues'][:10], 1):
                self.stdout.write(f"  {i}. {issue}")
        
        if result['suggestions']:
            self.stdout.write("\nSuggestions:")
            for i, suggestion in enumerate(result['suggestions'][:5], 1):
                self.stdout.write(f"  {i}. {suggestion}")
        
        self.stdout.write('-' * 60)

    def test_validation_and_fixing(self):
        self.stdout.write(self.style.SUCCESS('TESTING VALIDATION AND FIXING:'))
        self.stdout.write('=' * 60)

        # Test with fixable content
        fixable_content = {
            "title": "Earthquake Map",
            "description": "Map showing recent earthquakes", 
            "main_content": """
                <div class="container">
                    <h1>Earthquake Data</h1>
                    <div class="row">
                        <div class="col-8">
                            <!-- Map will be added here -->
                        </div>
                        <div class="col-4">
                            <!-- Chart will be added here -->
                        </div>
                    </row>
                </div>
            """,
            "custom_css": """
                .earthquake-map { height: 500px; width: 100%; }
                .chart-area { height: 300px; }
            """,
            "custom_js": """
                // Initialize map
                const map = L.map('earthquakeMap').setView([0, 0], 2);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map)
                
                // Initialize chart
                const ctx = document.getElementById('earthquakeChart').getContext('2d')
                const chart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Jan', 'Feb', 'Mar'],
                        datasets: [{
                            label: 'Earthquakes',
                            data: [12, 19, 3]
                        }]
                    }
                })
            """
        }

        # Run validation and fixing
        validation_agent = ValidationAgent()
        result = validation_agent.validate_and_fix(fixable_content)

        self.stdout.write(f"Validation and fixing completed:")
        self.stdout.write(f"  Success: {result['success']}")
        self.stdout.write(f"  Content fixed: {result['content_fixed']}")
        self.stdout.write(f"  Message: {result['message']}")

        if result.get('improvements'):
            improvements = result['improvements']
            self.stdout.write(f"\nImprovements made:")
            self.stdout.write(f"  Issues fixed: {improvements['issues_fixed']}")
            self.stdout.write(f"  Original issues: {improvements['original_issues']}")
            self.stdout.write(f"  Remaining issues: {improvements['remaining_issues']}")
            self.stdout.write(f"  Severity improved: {improvements['severity_improved']}")

        if result.get('final_validation'):
            final_val = result['final_validation']
            self.stdout.write(f"\nFinal validation:")
            self.stdout.write(f"  Total issues: {final_val['total_issues']}")
            self.stdout.write(f"  Severity: {final_val['overall_severity']}")

            if final_val.get('issues'):
                self.stdout.write("\nRemaining issues:")
                for issue in final_val['issues'][:5]:
                    self.stdout.write(f"  • {issue}")

        self.stdout.write('-' * 60)