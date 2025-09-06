from django.core.management.base import BaseCommand
from generator.models import HTMLTemplate


class Command(BaseCommand):
    help = 'Create enhanced base templates with pre-loaded libraries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing templates'
        )

    def handle(self, *args, **options):
        if options['overwrite']:
            HTMLTemplate.objects.all().delete()
            self.stdout.write(self.style.WARNING('Deleted all existing templates'))

        self.create_map_template()
        self.create_dashboard_template()
        self.create_generic_template()
        
        self.stdout.write(self.style.SUCCESS('Enhanced templates created successfully!'))

    def create_map_template(self):
        """Create enhanced map template with Leaflet pre-loaded"""
        
        required_libraries = [
            {
                "name": "Leaflet CSS",
                "type": "css",
                "url": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
            },
            {
                "name": "Leaflet JS", 
                "type": "js",
                "url": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            },
            {
                "name": "Chart.js",
                "type": "js",
                "url": "https://cdn.jsdelivr.net/npm/chart.js"
            },
            {
                "name": "Bootstrap CSS",
                "type": "css", 
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
            },
            {
                "name": "Bootstrap JS",
                "type": "js",
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
            },
            {
                "name": "Font Awesome",
                "type": "css",
                "url": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
            }
        ]

        template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    
    <!-- Pre-loaded Libraries - ALL COMMON LIBRARIES -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        #map { height: 500px; width: 100%; }
        .info-panel { max-height: 400px; overflow-y: auto; }
        .loading { display: none; }
        .error { color: #dc3545; }
        {{CUSTOM_CSS}}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <h1 class="text-center mb-4">{{TITLE}}</h1>
                <p class="text-muted text-center">{{DESCRIPTION}}</p>
            </div>
        </div>
        
        <div class="row">
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-map-marked-alt"></i> Map View</h5>
                    </div>
                    <div class="card-body p-0">
                        <div id="map"></div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-list"></i> Information Panel</h5>
                    </div>
                    <div class="card-body info-panel" id="infoPanel">
                        <div class="loading" id="loading">
                            <div class="spinner-border" role="status"></div>
                            <span>Loading data...</span>
                        </div>
                        <div id="content">
                            {{MAIN_CONTENT}}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Pre-loaded JavaScript Libraries - ALL READY TO USE -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Initialize map (Leaflet is already loaded)
        const map = L.map('map').setView([0, 0], 2);
        
        // Add base tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        // Utility functions for common map operations
        function addMarker(lat, lng, popupContent) {
            return L.marker([lat, lng]).addTo(map).bindPopup(popupContent);
        }
        
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }
        
        function showError(message) {
            const content = document.getElementById('content');
            content.innerHTML = `<div class="alert alert-danger error"><i class="fas fa-exclamation-triangle"></i> ${message}</div>`;
        }
        
        {{CUSTOM_JS}}
    </script>
</body>
</html>"""

        css_template = """
/* Map-specific styles */
.leaflet-popup-content { font-size: 14px; }
.marker-icon { background-color: #dc3545; }
.info-item { 
    border-bottom: 1px solid #eee; 
    padding: 10px 0; 
}
.info-item:last-child { border-bottom: none; }
"""

        js_template = """
// Map utility functions
function centerMapOn(lat, lng, zoom = 10) {
    map.setView([lat, lng], zoom);
}

function clearMarkers() {
    map.eachLayer(function(layer) {
        if (layer instanceof L.Marker) {
            map.removeLayer(layer);
        }
    });
}

function addDataToMap(data) {
    // Override this function with specific data handling
    console.log('Data received:', data);
}
"""

        template, created = HTMLTemplate.objects.get_or_create(
            name="Enhanced Map Template",
            template_type="map",
            defaults={
                'description': "Map visualization template with Leaflet pre-loaded and ready to use",
                'template_content': template_content,
                'required_libraries': required_libraries,
                'css_template': css_template,
                'js_template': js_template,
                'is_active': True
            }
        )
        
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} Enhanced Map Template")

    def create_dashboard_template(self):
        """Create enhanced dashboard template with Chart.js pre-loaded"""
        
        required_libraries = [
            {
                "name": "Chart.js",
                "type": "js",
                "url": "https://cdn.jsdelivr.net/npm/chart.js"
            },
            {
                "name": "Bootstrap CSS",
                "type": "css",
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
            },
            {
                "name": "Bootstrap JS",
                "type": "js", 
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
            },
            {
                "name": "Font Awesome",
                "type": "css",
                "url": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
            }
        ]

        template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    
    <!-- Pre-loaded Libraries -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .chart-container { position: relative; height: 400px; }
        .stat-card { border-left: 4px solid #007bff; }
        .loading { display: none; }
        {{CUSTOM_CSS}}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <h1 class="text-center mb-4">{{TITLE}}</h1>
                <p class="text-muted text-center">{{DESCRIPTION}}</p>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-chart-line"></i> Metric 1</h5>
                        <h3 id="metric1">--</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-chart-bar"></i> Metric 2</h5>
                        <h3 id="metric2">--</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-chart-pie"></i> Metric 3</h5>
                        <h3 id="metric3">--</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-chart-area"></i> Metric 4</h5>
                        <h3 id="metric4">--</h3>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line"></i> Main Chart</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="mainChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-list"></i> Data Summary</h5>
                    </div>
                    <div class="card-body">
                        <div class="loading" id="loading">
                            <div class="spinner-border" role="status"></div>
                            <span>Loading data...</span>
                        </div>
                        <div id="summary">
                            {{MAIN_CONTENT}}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Pre-loaded JavaScript Libraries -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Initialize chart (Chart.js is already loaded)
        const ctx = document.getElementById('mainChart').getContext('2d');
        const mainChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Data',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
        
        // Utility functions
        function updateMetric(metricId, value) {
            document.getElementById(metricId).textContent = value;
        }
        
        function updateChart(labels, data) {
            mainChart.data.labels = labels;
            mainChart.data.datasets[0].data = data;
            mainChart.update();
        }
        
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }
        
        {{CUSTOM_JS}}
    </script>
</body>
</html>"""

        template, created = HTMLTemplate.objects.get_or_create(
            name="Enhanced Dashboard Template",
            template_type="dashboard", 
            defaults={
                'description': "Dashboard template with Chart.js pre-loaded for data visualization",
                'template_content': template_content,
                'required_libraries': required_libraries,
                'is_active': True
            }
        )
        
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} Enhanced Dashboard Template")

    def create_generic_template(self):
        """Create comprehensive template with ALL common libraries"""
        
        required_libraries = [
            {
                "name": "Leaflet CSS",
                "type": "css",
                "url": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
            },
            {
                "name": "Leaflet JS",
                "type": "js",
                "url": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            },
            {
                "name": "Chart.js",
                "type": "js",
                "url": "https://cdn.jsdelivr.net/npm/chart.js"
            },
            {
                "name": "Bootstrap CSS",
                "type": "css",
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
            },
            {
                "name": "Bootstrap JS",
                "type": "js",
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
            },
            {
                "name": "Font Awesome",
                "type": "css", 
                "url": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
            }
        ]

        template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    
    <!-- Pre-loaded Libraries - ALL COMMON LIBRARIES INCLUDED -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        #map { height: 500px; width: 100%; margin-bottom: 20px; }
        .chart-container { position: relative; height: 400px; margin-bottom: 20px; }
        .loading { display: none; }
        .error { color: #dc3545; }
        .info-panel { max-height: 400px; overflow-y: auto; }
        {{CUSTOM_CSS}}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <h1 class="text-center mb-4">{{TITLE}}</h1>
                <p class="text-muted text-center">{{DESCRIPTION}}</p>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="loading text-center" id="loading">
                    <div class="spinner-border" role="status"></div>
                    <p>Loading data...</p>
                </div>
                
                <div id="content">
                    {{MAIN_CONTENT}}
                </div>
            </div>
        </div>
    </div>

    <!-- Pre-loaded JavaScript Libraries - ALL READY TO USE -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // ALL LIBRARIES ARE LOADED AND READY:
        // - Leaflet: Use L.map(), L.marker(), etc.
        // - Chart.js: Use new Chart(), etc.
        // - Bootstrap: All CSS classes and JS components available
        
        // Utility functions
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }
        
        function showError(message) {
            const content = document.getElementById('content');
            content.innerHTML = `<div class="alert alert-danger error"><i class="fas fa-exclamation-triangle"></i> ${message}</div>`;
        }
        
        // Map utilities (Leaflet ready)
        function createMap(elementId, lat = 0, lng = 0, zoom = 2) {
            const map = L.map(elementId).setView([lat, lng], zoom);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            return map;
        }
        
        function addMarker(map, lat, lng, popupContent) {
            return L.marker([lat, lng]).addTo(map).bindPopup(popupContent);
        }
        
        // Chart utilities (Chart.js ready)
        function createChart(elementId, type, data, options = {}) {
            const ctx = document.getElementById(elementId).getContext('2d');
            return new Chart(ctx, {
                type: type,
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    ...options
                }
            });
        }
        
        {{CUSTOM_JS}}
    </script>
</body>
</html>"""

        template, created = HTMLTemplate.objects.get_or_create(
            name="Comprehensive Template",
            template_type="generic",
            defaults={
                'description': "Comprehensive template with Leaflet, Chart.js, Bootstrap, and Font Awesome all pre-loaded",
                'template_content': template_content,
                'required_libraries': required_libraries,
                'is_active': True
            }
        )
        
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} Comprehensive Template")