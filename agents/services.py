try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    OpenAI = None
    openai_available = False

from django.conf import settings
from typing import Dict, Any, Optional
import json


class LLMService:
    """Basic LLM service for generating HTML content"""
    
    def __init__(self):
        self.client = None
        if openai_available and settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def get_available_datasets_context(self) -> str:
        """Get rich context about available datasets for LLM prompt"""
        from datasets.models import DataSource
        
        active_sources = DataSource.objects.filter(is_active=True).order_by('category', 'name')
        
        if not active_sources.exists():
            return "No configured data sources available. Please configure DataSources first."
        
        context_parts = ["AVAILABLE DATA SOURCES (integrate these real APIs):"]
        
        current_category = None
        for source in active_sources:
            if source.category != current_category:
                current_category = source.category
                category_name = dict(source.CATEGORY_CHOICES).get(source.category, source.category)
                context_parts.append(f"\n**{category_name.upper()}:**")
            
            # Get the detailed LLM context for each source
            source_context = source.get_llm_context_summary()
            context_parts.append(f"• {source_context}")
            
            # Add query patterns if available
            if source.query_patterns:
                context_parts.append("  Query patterns:")
                for pattern in source.query_patterns[:2]:  # Limit to first 2 patterns
                    context_parts.append(f"    - {pattern.get('name', 'Query')}: {pattern.get('template', '')}")
            
            context_parts.append("")  # Empty line for readability
        
        return "\n".join(context_parts)
    
    def generate_html_content(self, user_request: str, template_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate HTML content based on user request and template context
        Returns a dictionary with template variables to fill
        """
        
        system_prompt = f"""
        You are an expert disaster response application developer. You create comprehensive, data-driven web applications that integrate real external data sources for emergency management.

        YOUR TASK: Build a complete, functional disaster response webpage that:
        1. Identifies and integrates relevant real-time data sources
        2. Includes interactive elements (maps, charts, live data feeds)
        3. Provides actionable information with specific resources and contacts
        4. Uses realistic URLs, phone numbers, and data that would exist for the scenario

        {self.get_available_datasets_context()}

        REQUIREMENTS FOR YOUR RESPONSE:
        1. Research the specific location/disaster type mentioned
        2. Include multiple real data source integrations via JavaScript
        3. Add interactive maps using Leaflet with real coordinates
        4. Create charts with Chart.js showing relevant data trends
        5. Include emergency contact numbers and shelter locations
        6. Add news feeds or recent updates about the situation
        7. Make it mobile-responsive with clear call-to-action buttons

        Return ONLY a valid JSON object (no markdown, no explanations) with these exact fields:
        {{
          "title": "Specific, actionable page title",
          "description": "Clear description of the app's purpose and data sources", 
          "main_content": "Complete HTML with real API calls, maps, charts, contact info",
          "custom_css": "Styling for interactive elements and mobile responsiveness",
          "custom_js": "JavaScript for data fetching, map rendering, chart creation"
        }}

        EXAMPLE INTEGRATIONS TO INCLUDE:
        - Live weather data with fetch() calls to weather APIs
        - Interactive maps with markers for shelters, hazards, resources
        - Charts showing trends (temperature, earthquake frequency, etc.)
        - Auto-refreshing emergency alerts
        - Social media feeds or news RSS integration
        - Contact forms or resource request buttons
        """
        
        user_prompt = f"""
        CREATE A COMPREHENSIVE DISASTER RESPONSE APPLICATION FOR: {user_request}

        SPECIFIC REQUIREMENTS:
        1. Research this specific scenario and location (if mentioned)
        2. Integrate at least 3-4 relevant real data sources with working JavaScript API calls
        3. Include an interactive map with specific coordinates and markers
        4. Add charts/graphs showing relevant data trends or statistics  
        5. Provide real emergency contacts, shelters, or resource centers
        6. Include recent news or social media feeds related to this scenario
        7. Add functional elements like search, filtering, or user input forms
        8. Make it look professional and production-ready, not a demo

        MAKE IT REALISTIC: Use actual API endpoints, real coordinates, existing emergency phone numbers, actual shelter names/addresses, real news sources, etc. This should look like a real application someone would deploy during an emergency.

        Focus on immediate actionable information that saves lives and helps communities respond effectively.
        """
        
        try:
            if not self.client:
                # Fallback for testing without API key
                return self._generate_fallback_content(user_request)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from markdown code blocks if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Try to parse as JSON, fallback to structured response
            try:
                parsed_content = json.loads(content)
                
                # Validate required fields
                required_fields = ['title', 'description', 'main_content', 'custom_css', 'custom_js']
                for field in required_fields:
                    if field not in parsed_content:
                        parsed_content[field] = ""
                
                return parsed_content
                
            except json.JSONDecodeError as e:
                print(f"JSON Parse Error: {e}")
                print(f"Raw content: {content[:200]}...")
                return self._parse_text_response(content, user_request)
                
        except Exception as e:
            print(f"LLM Error: {e}")
            return self._generate_fallback_content(user_request)
    
    def _generate_fallback_content(self, user_request: str) -> Dict[str, Any]:
        """Generate fallback content when LLM is not available"""
        return {
            "title": f"Emergency Response: {user_request}",
            "description": f"This page provides information and resources for: {user_request}",
            "main_content": f"""
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-warning">
                            <h5 class="mb-0"><i class="fas fa-exclamation-triangle"></i> Emergency Information</h5>
                        </div>
                        <div class="card-body">
                            <h6>Request: {user_request}</h6>
                            <p>This is a demonstration page generated for: <strong>{user_request}</strong></p>
                            <p>In a real scenario, this would show:</p>
                            <ul>
                                <li>Real-time data from relevant APIs</li>
                                <li>Interactive maps and charts</li>
                                <li>Contact information and resources</li>
                                <li>Action items and emergency procedures</li>
                            </ul>
                            <div class="alert alert-primary">
                                <strong>Note:</strong> Configure your OpenAI API key to enable AI-generated content.
                            </div>
                        </div>
                    </div>
                </div>
            """,
            "custom_css": """
                .card-header.bg-warning {
                    color: #000;
                }
            """,
            "custom_js": """
                console.log('LL-HTML Demo Page Loaded');
            """
        }
    
    def _parse_text_response(self, content: str, user_request: str) -> Dict[str, Any]:
        """Parse non-JSON LLM responses"""
        return {
            "title": f"AI Response: {user_request}",
            "description": "AI-generated disaster response content",
            "main_content": f"""
                <div class="col-12">
                    <div class="card">
                        <div class="card-body">
                            <pre>{content}</pre>
                        </div>
                    </div>
                </div>
            """,
            "custom_css": "",
            "custom_js": ""
        }