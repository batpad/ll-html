import json
import time
from typing import Dict, Any, List, Optional, Union
from django.conf import settings
from django.utils import timezone
import logging

from .tools import tool_registry, AgentTool
from .models import AgentSession, AgentMessage

try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    OpenAI = None
    openai_available = False

logger = logging.getLogger(__name__)


class ReactAgent:
    """
    REACT (Reason-Act-Observe) agent that uses tools to gather information 
    before generating final HTML content
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"agent_{int(time.time())}"
        self.max_iterations = settings.AGENT_MAX_ITERATIONS
        self.max_llm_calls = settings.AGENT_MAX_LLM_CALLS
        self.llm_calls_made = 0
        self.iterations_completed = 0
        
        # Initialize OpenAI client
        self.client = None
        if openai_available and settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Agent context - accumulates knowledge over iterations
        self.context = {
            "user_request": "",
            "gathered_intelligence": {},
            "tool_results": [],
            "reasoning_steps": [],
            "available_data_sources": self._get_data_sources_context(),
            "available_templates": self._get_available_templates_context(),
            "ready_to_generate": False
        }
        
        # Get or create agent session
        self.session = self._get_or_create_session()
    
    def _get_or_create_session(self) -> AgentSession:
        """Get or create an agent session"""
        session, created = AgentSession.objects.get_or_create(
            session_id=self.session_id,
            defaults={
                'context': self.context,
                'current_task': '',
                'task_status': 'initialized'
            }
        )
        
        if not created:
            # Load existing context
            self.context.update(session.context)
        
        return session
    
    def _save_session(self):
        """Save current context to session"""
        self.session.context = self.context
        self.session.updated_at = timezone.now()
        self.session.save()
    
    def _log_message(self, message_type: str, content: str, metadata: Dict[str, Any] = None):
        """Log a message to the agent session"""
        AgentMessage.objects.create(
            session=self.session,
            message_type=message_type,
            content=content,
            metadata=metadata or {}
        )
    
    def _get_data_sources_context(self) -> str:
        """Get available data sources context with strong priority emphasis"""
        from datasets.models import DataSource
        
        active_sources = DataSource.objects.filter(is_active=True).order_by('category', 'name')
        
        if not active_sources.exists():
            return "No configured data sources available."
        
        context_parts = [
            "🎯 PRIORITY DATA SOURCES - USE THESE FIRST:",
            "=" * 50,
            "These are CONFIGURED, VALIDATED data sources that should be your PRIMARY choice.",
            "Only use external sources if these don't have the needed data.",
        ]
        
        current_category = None
        total_collections = 0
        
        for source in active_sources:
            if source.category != current_category:
                current_category = source.category
                category_name = dict(source.CATEGORY_CHOICES).get(source.category, source.category)
                context_parts.append(f"\n📊 {category_name.upper()}:")
            
            context_parts.append(f"✅ {source.name}: {source.description}")
            
            if source.is_stac_catalog():
                collections = source.get_available_collections()
                total_collections += len(collections)
                
                context_parts.append(f"   🔗 STAC Search URL: {source.get_stac_search_url()}")
                context_parts.append(f"   📋 Available Collections ({len(collections)} total):")
                
                # Group collections by type and show them more descriptively
                collection_groups = {
                    'events': [c for c in collections if 'events' in c.lower()],
                    'hazards': [c for c in collections if 'hazard' in c.lower()], 
                    'impacts': [c for c in collections if 'impact' in c.lower()],
                    'other': [c for c in collections if not any(x in c.lower() for x in ['events', 'hazard', 'impact'])]
                }
                
                for group_name, group_collections in collection_groups.items():
                    if group_collections:
                        context_parts.append(f"     📊 {group_name.title()}: {', '.join(group_collections[:3])}")
                        if len(group_collections) > 3:
                            context_parts.append(f"         ... and {len(group_collections) - 3} more {group_name}")
                
                # Add specific usage examples with real collection names
                example_collections = collections[:2]
                context_parts.append(f"   💡 Usage Examples:")
                for coll in example_collections:
                    context_parts.append(f"     • fetch_stac_sample_data(collection='{coll}', limit=3)")
                    
                context_parts.append(f"   ⚡ PRIORITY: Always fetch sample data from these collections FIRST")
            
            if source.llm_context:
                context_parts.append(f"   📝 Context: {source.llm_context}")
        
        context_parts.extend([
            "",
            "=" * 50,
            f"🚨 CRITICAL: These {active_sources.count()} configured sources contain {total_collections} data collections.",
            "ALWAYS check these sources BEFORE searching for external alternatives.",
            "Use 'fetch_stac_sample_data' tool to get real data structure and examples."
        ])
        
        return "\n".join(context_parts)
    
    def _get_available_templates_context(self) -> str:
        """Get available HTML templates and their pre-loaded libraries"""
        from generator.models import HTMLTemplate
        
        active_templates = HTMLTemplate.objects.filter(is_active=True).order_by('template_type', 'name')
        
        if not active_templates.exists():
            return "No HTML templates available - will generate from scratch."
        
        context_parts = [
            "🎯 ALL COMMON LIBRARIES ARE PRE-LOADED:",
            "=" * 50,
            "Every template includes ALL major libraries ready to use:",
            "",
            "✅ LEAFLET (Maps): Use L.map(), L.marker(), etc. directly",
            "✅ CHART.JS (Charts): Use new Chart() directly", 
            "✅ BOOTSTRAP (Styling): All CSS classes & JS components available",
            "✅ FONT AWESOME (Icons): Use <i class='fas fa-icon'></i>",
            "",
            f"📋 {active_templates.count()} templates available:",
            "• Enhanced Map Template (map layouts with utility functions)",
            "• Enhanced Dashboard Template (dashboard layouts with metrics)",
            "• Comprehensive Template (flexible general-purpose layout)",
            "",
            "=" * 50,
            "🚨 CRITICAL: Libraries are ALREADY loaded - DON'T add <script> or <link> tags!",
            "• Use L.map('elementId') for maps (Leaflet ready)",
            "• Use new Chart(ctx, config) for charts (Chart.js ready)",
            "• Use Bootstrap classes like 'container', 'btn', 'card' (Bootstrap ready)",
            "• All templates include utility functions: createMap(), createChart(), showLoading()",
        ]
        
        return "\n".join(context_parts)
    
    def execute(self, user_request: str) -> Dict[str, Any]:
        """
        Execute the REACT loop to gather information and generate final response
        """
        self.context["user_request"] = user_request
        self.session.current_task = user_request
        self.session.task_status = 'executing'
        self._save_session()
        
        self._log_message("user", user_request)
        
        try:
            # PLANNING PHASE: First understand and plan the request
            if not self.context.get("planning_completed", False):
                planning_result = self._create_implementation_plan()
                if planning_result.get("success"):
                    self.context["implementation_plan"] = planning_result["plan"]
                    self.context["planning_completed"] = True
                    self._log_message("agent", f"Created implementation plan: {planning_result['plan']['summary']}")
                else:
                    return {
                        "success": False,
                        "error": f"Planning failed: {planning_result.get('error', 'Unknown error')}"
                    }
            
            # REACT Loop
            while (self.iterations_completed < self.max_iterations and 
                   self.llm_calls_made < self.max_llm_calls and 
                   not self.context["ready_to_generate"]):
                
                self.iterations_completed += 1
                logger.info(f"REACT iteration {self.iterations_completed}")
                
                # Reason: Ask LLM what to do next
                action = self._reason_about_next_step()
                
                if action.get("action") == "generate_final_html":
                    self.context["ready_to_generate"] = True
                    break
                
                # Act: Execute the chosen tool
                if action.get("action") and action.get("action") != "no_action":
                    tool_result = self._execute_tool(action)
                    
                    # Observe: Add results to context
                    self.context["tool_results"].append({
                        "iteration": self.iterations_completed,
                        "action": action,
                        "result": tool_result,
                        "timestamp": timezone.now().isoformat()
                    })
                
                self._save_session()
            
            # Generate final HTML using gathered intelligence
            final_result = self._generate_final_html()
            
            self.session.task_status = 'completed'
            self._save_session()
            
            return final_result
            
        except Exception as e:
            logger.error(f"REACT agent execution failed: {e}")
            self.session.task_status = 'failed'
            self._save_session()
            
            return {
                "success": False,
                "error": str(e),
                "context": self.context
            }
    
    def _reason_about_next_step(self) -> Dict[str, Any]:
        """
        Ask the LLM to reason about what to do next based on current context
        """
        if not self.client or self.llm_calls_made >= self.max_llm_calls:
            return {"action": "generate_final_html", "reasoning": "LLM calls exhausted"}
        
        # Build reasoning prompt with implementation plan
        implementation_plan = self.context.get('implementation_plan', {})
        plan_summary = implementation_plan.get('summary', 'No plan available')
        research_tasks = implementation_plan.get('research_tasks', [])
        data_requirements = implementation_plan.get('data_requirements', [])
        
        system_prompt = f"""
        You are a REACT agent executing a planned disaster response application implementation.
        
        IMPLEMENTATION PLAN:
        {plan_summary}
        
        DATA REQUIREMENTS:
        {chr(10).join('- ' + req for req in data_requirements) if data_requirements else '- No specific requirements identified'}
        
        RESEARCH TASKS TO COMPLETE:
        {chr(10).join('- ' + task for task in research_tasks) if research_tasks else '- No specific research tasks identified'}
        
        Current task: {self.context['user_request']}
        
        Available tools:
        {self._get_tools_description()}
        
        {self.context['available_data_sources']}
        
        {self.context['available_templates']}
        
        🎯 PLAN-DRIVEN APPROACH:
        - Follow the implementation plan to guide your research
        - Complete the specific research tasks identified in the plan
        - Gather the data sources specified in the data requirements
        - Validate that you can fulfill the planned functional requirements
        - ONLY generate HTML once you have completed the planned research
        
        📋 RESEARCH PRIORITY (based on plan):
        1. FIRST: Complete research tasks from implementation plan
        2. SECOND: Validate data requirements can be met with available sources
        3. THIRD: Gather any supplementary information needed
        
        ONLY decide to "generate_final_html" if you have:
        1. Completed the research tasks from your implementation plan
        2. Validated that data requirements can be satisfied
        3. At least 3 successful tool calls completed
        4. Confidence that the plan can be executed with gathered intelligence
        
        Return a JSON object with:
        - "reasoning": Your detailed thought process (reference the implementation plan)
        - "action": Tool name to use (web_search, validate_api_endpoint, fetch_stac_sample_data, etc.)
        - "parameters": Parameters for the tool
        - "continue": true (always true until plan research is complete)
        """
        
        # Include previous context
        context_summary = self._build_context_summary()
        
        user_prompt = f"""
        Context so far:
        {context_summary}
        
        Based on the implementation plan, what should I do next to complete the research phase?
        
        Review the implementation plan and consider:
        1. Which research tasks from the plan have I completed?
        2. Which data requirements do I still need to validate?
        3. What specific information is still missing to execute the plan?
        4. Am I ready to generate the application based on the plan and gathered intelligence?
        
        Focus on completing the planned research systematically rather than random exploration.
        
        Respond with valid JSON only.
        """
        
        try:
            self.llm_calls_made += 1
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=getattr(settings, 'AGENT_MAX_TOKENS_REASONING', 2000)
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean JSON from markdown if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Parse JSON with error handling
            try:
                action = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in reasoning step: {e}")
                # For reasoning steps, return a safe fallback
                return {
                    "action": "no_action",
                    "reasoning": f"JSON parsing failed: {str(e)}",
                    "continue": True
                }
            
            # Enforce data source priority and minimum tool usage
            successful_tool_calls = len([r for r in self.context["tool_results"] if r.get("result", {}).get("success", False)])
            stac_calls_made = len([r for r in self.context["tool_results"] 
                                 if r.get("action", {}).get("action") == "fetch_stac_sample_data" 
                                 and r.get("result", {}).get("success", False)])
            
            # Block HTML generation if insufficient research or no STAC data fetched
            if action.get("action") == "generate_final_html":
                if successful_tool_calls < 2:
                    self._log_message("agent", f"Blocked early HTML generation - only {successful_tool_calls} successful tool calls")
                    action = {
                        "action": "no_action",
                        "reasoning": f"Insufficient research completed ({successful_tool_calls} successful tool calls). Must gather more intelligence using available tools before generating HTML.",
                        "continue": True
                    }
                elif stac_calls_made == 0:
                    self._log_message("agent", "Blocked HTML generation - must fetch STAC data from configured sources first")
                    action = {
                        "action": "no_action", 
                        "reasoning": "Must fetch sample data from configured STAC sources before generating HTML. Use 'fetch_stac_sample_data' tool first to understand available data structure.",
                        "continue": True
                    }
            
            self._log_message("agent", f"Reasoning: {action.get('reasoning', '')}")
            self.context["reasoning_steps"].append({
                "iteration": self.iterations_completed,
                "reasoning": action.get("reasoning", ""),
                "action": action.get("action", ""),
                "timestamp": timezone.now().isoformat()
            })
            
            return action
            
        except Exception as e:
            logger.error(f"Reasoning step failed: {e}")
            return {
                "action": "generate_final_html",
                "reasoning": f"Error in reasoning: {str(e)}",
                "continue": False
            }
    
    def _execute_tool(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool based on the action"""
        tool_name = action.get("action")
        parameters = action.get("parameters", {})
        
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        try:
            # Validate and fix parameters format
            if not isinstance(parameters, dict):
                logger.warning(f"Tool {tool_name} received non-dict parameters: {type(parameters)} - {parameters}")
                # Try to fix common parameter issues
                if isinstance(parameters, str):
                    # For web_search, if it's just a query string, wrap it properly
                    if tool_name == "web_search":
                        parameters = {"query": parameters}
                    else:
                        # For other tools, return error
                        return {
                            "success": False,
                            "error": f"Invalid parameters format: expected dict, got string",
                            "tool": tool_name,
                            "raw_parameters": str(parameters)
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Invalid parameters format: expected dict, got {type(parameters).__name__}",
                        "tool": tool_name,
                        "raw_parameters": str(parameters)
                    }
            
            result = tool.execute(**parameters)
            self._log_message("tool", f"Executed {tool_name}", {"parameters": parameters, "result": result})
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "parameters": parameters
            }
            self._log_message("tool", f"Tool {tool_name} failed: {str(e)}")
            return error_result
    
    def _build_context_summary(self) -> str:
        """Build a summary of gathered context for the LLM"""
        summary_parts = []
        
        if self.context["tool_results"]:
            summary_parts.append("Information gathered:")
            for i, result in enumerate(self.context["tool_results"][-3:], 1):  # Last 3 results
                action = result["action"]
                tool_result = result["result"]
                
                if tool_result.get("success"):
                    summary_parts.append(f"{i}. {action.get('action', 'Unknown')}: {self._summarize_tool_result(tool_result)}")
                else:
                    summary_parts.append(f"{i}. {action.get('action', 'Unknown')}: Failed - {tool_result.get('error', 'Unknown error')}")
        
        return "\n".join(summary_parts) if summary_parts else "No information gathered yet."
    
    def _summarize_tool_result(self, result: Dict[str, Any]) -> str:
        """Create a brief summary of tool result for context"""
        if "results" in result and isinstance(result["results"], list):
            # Web search results
            return f"Found {len(result['results'])} web results"
        elif "sample_features" in result:
            # STAC data results
            return f"Found {result.get('total_found', 0)} data items with properties: {', '.join(result.get('available_properties', [])[:5])}"
        elif "is_accessible" in result:
            # API validation results
            status = "accessible" if result.get("is_accessible") else "not accessible"
            return f"API endpoint is {status} (status: {result.get('status_code', 'unknown')})"
        else:
            return "Data retrieved successfully"
    
    def _get_tools_description(self) -> str:
        """Get description of available tools"""
        tools = tool_registry.get_available_tools()
        descriptions = []
        
        for tool_name, tool in tools.items():
            descriptions.append(f"- {tool_name}: {tool.description}")
        
        return "\n".join(descriptions)
    
    def _create_implementation_plan(self) -> Dict[str, Any]:
        """
        Create a detailed implementation plan based on the user request
        """
        if not self.client or self.llm_calls_made >= self.max_llm_calls:
            return {
                "success": False,
                "error": "OpenAI client not available or LLM calls exhausted"
            }
        
        system_prompt = f"""
        You are an expert disaster response application planner. Your job is to analyze user requests and create detailed implementation plans.

        {self.context['available_data_sources']}

        PLANNING REQUIREMENTS:
        1. Parse the user request to understand exactly what they want
        2. Define specific functional requirements 
        3. Identify what data sources and APIs are needed
        4. Plan the user interface and interaction design
        5. Outline the technical implementation approach

        Create a comprehensive plan that will guide the research and implementation phases.
        
        Return ONLY a valid JSON object with this structure:
        {{
          "summary": "Brief summary of what will be built",
          "user_intent": "Clear interpretation of what the user wants",
          "functional_requirements": [
            "Specific requirement 1",
            "Specific requirement 2"
          ],
          "data_requirements": [
            "Data source 1 needed",
            "Data source 2 needed"
          ],
          "ui_components": [
            "UI component 1 (e.g., interactive map)",
            "UI component 2 (e.g., data filters)"
          ],
          "research_tasks": [
            "Research task 1 to validate data availability",
            "Research task 2 to find current information"
          ],
          "success_criteria": [
            "Criteria 1 for successful implementation",
            "Criteria 2 for successful implementation"
          ]
        }}
        """
        
        user_prompt = f"""
        User Request: {self.context['user_request']}
        
        Analyze this request and create a detailed implementation plan. Focus on:
        1. What exactly does the user want to accomplish?
        2. What specific features and functionality are needed?
        3. What data sources from our configured options should be used?
        4. What research is needed to ensure accurate, current information?
        5. How should the interface be designed for the best user experience?
        
        Be specific and actionable in your plan.
        """
        
        try:
            self.llm_calls_made += 1
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Lower temperature for more consistent planning
                max_tokens=getattr(settings, 'AGENT_MAX_TOKENS_PLANNING', 2000)
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean JSON from markdown if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Parse JSON with error handling
            try:
                plan = json.loads(content)
                return {
                    "success": True,
                    "plan": plan
                }
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in planning step: {e}")
                return {
                    "success": False,
                    "error": f"Failed to parse planning JSON: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Planning step failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_final_html(self) -> Dict[str, Any]:
        """Generate the final HTML using all gathered intelligence"""
        if not self.client:
            return {
                "success": False,
                "error": "OpenAI client not available"
            }
        
        # Build comprehensive context for HTML generation
        intelligence_summary = self._build_intelligence_summary()
        implementation_plan = self.context.get('implementation_plan', {})
        
        # Extract key components from the plan
        plan_summary = implementation_plan.get('summary', 'Application based on user request')
        functional_requirements = implementation_plan.get('functional_requirements', [])
        ui_components = implementation_plan.get('ui_components', [])
        success_criteria = implementation_plan.get('success_criteria', [])
        
        system_prompt = f"""
        You are an expert web application developer implementing a planned application.

        IMPLEMENTATION PLAN TO EXECUTE:
        Summary: {plan_summary}
        
        FUNCTIONAL REQUIREMENTS TO IMPLEMENT:
        {chr(10).join('- ' + req for req in functional_requirements) if functional_requirements else '- No specific requirements specified'}
        
        UI COMPONENTS TO INCLUDE:
        {chr(10).join('- ' + comp for comp in ui_components) if ui_components else '- Components as needed for functionality'}
        
        SUCCESS CRITERIA:
        {chr(10).join('- ' + crit for crit in success_criteria) if success_criteria else '- Functional application with real data'}

        {self.context['available_data_sources']}

        GATHERED INTELLIGENCE:
        {intelligence_summary}

        Create a complete, functional webpage that IMPLEMENTS THE PLAN:
        1. Fulfills ALL functional requirements from the implementation plan
        2. Includes ALL specified UI components  
        3. Uses the ACTUAL information you've gathered through research
        4. Integrates with verified data sources and APIs
        5. Meets the success criteria defined in the plan

        ⚠️ CRITICAL URL REQUIREMENTS ⚠️:
        - ONLY use EXACT API endpoints discovered through your research
        - DO NOT modify, construct, or assume URL patterns
        - Copy URLs EXACTLY from your tool results
        - Add comments in JavaScript showing which research result provided each URL
        - Include comprehensive error handling for all API calls
        
        ⚠️ CRITICAL GEOJSON/MAP HANDLING ⚠️:
        - STAC GeoJSON often contains complex polygon geometries, not simple points
        - For polygons: extract centroid or first coordinate pair for markers
        - Always validate coordinates exist before creating markers
        - Example coordinate extraction:
        ```javascript
        function getCoordinates(geometry) {{
            if (geometry.type === 'Point') {{
                return geometry.coordinates; // [lng, lat]
            }} else if (geometry.type === 'Polygon') {{
                return geometry.coordinates[0][0]; // First point of first ring
            }}
            return null; // Handle other types
        }}
        ```

        ⚠️ CRITICAL TEMPLATE INJECTION UNDERSTANDING ⚠️:
        Your generated content will be injected into this template structure:
        
        ```html
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{{{{ title }}}}</title>
            <link href="https://unpkg.com/leaflet/dist/leaflet.css" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>{{{{ custom_css }}}}</style>
        </head>
        <body>
            {{{{ main_content }}}}
            <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>{{{{ custom_js }}}}</script>
        </body>
        </html>
        ```
        
        DO NOT generate <html>, <head>, or <body> tags - only the content that goes inside!
        
        Return ONLY a valid JSON object (no markdown, no explanations) with these exact fields:
        {{
          "title": "Specific, actionable page title based on research",
          "description": "Clear description incorporating gathered intelligence", 
          "main_content": "HTML body content ONLY (no html/head/body tags) with Bootstrap containers",
          "custom_css": "CSS rules ONLY (no <style> tags)",
          "custom_js": "JavaScript code ONLY (no <script> tags) with EXACT URLs from research"
        }}
        
        🚨 CRITICAL JSON FORMATTING:
        - Escape all backslashes in strings (use \\\\ for single \\)
        - Escape all quotes in strings (use \\" for ")
        - No line breaks inside JSON string values - use \\n instead
        - Ensure all braces and brackets are properly matched
        """
        
        user_prompt = f"""
        CREATE A COMPREHENSIVE DISASTER RESPONSE APPLICATION FOR: {self.context['user_request']}

        Use the intelligence I've gathered to create an accurate, functional application that incorporates:
        - Current news and events from web research
        - Validated API endpoints and data sources
        - Real data structures and sample content
        - Specific geographic information and coordinates
        - Recent developments and current situation

        🔗 URL VALIDATION REQUIREMENTS:
        - Every API call must reference a URL from your research results
        - Add JavaScript comments like: "// URL from STAC validation tool result"
        - Include the exact collection names and parameters you discovered
        - Use error handling: try/catch blocks with fallback messages
        - No invented endpoints - only researched ones

        🚨 LIBRARY USAGE EXAMPLES (all libraries are PRE-LOADED):
        ```javascript
        // MAPS (Leaflet is ready - MUST add OSM basemap):
        const map = L.map('mapId').setView([lat, lng], zoom);
        // REQUIRED: Add OpenStreetMap basemap to every map:
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        L.marker([lat, lng]).addTo(map).bindPopup('Info');
        
        // CHARTS (Chart.js is ready):
        const ctx = document.getElementById('chartId').getContext('2d');
        const chart = new Chart(ctx, {{ type: 'line', data: data }});
        
        // STYLING (Bootstrap is ready):
        <div class="card">
          <div class="card-header">Title</div>
          <div class="card-body">Content</div>
        </div>
        ```

        EXAMPLE of proper API call:
        ```javascript
        // URL validated by fetch_stac_sample_data tool - collection: gdacs-events
        const stacUrl = 'https://montandon-eoapi-stage.ifrc.org/stac/search';
        fetch(stacUrl + '?collections=gdacs-events&bbox=88,20,93,27')
        ```

        Make this a production-ready application that provides real value for disaster response.
        """
        
        try:
            self.llm_calls_made += 1
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=getattr(settings, 'AGENT_MAX_TOKENS_FINAL_GENERATION', 6000)
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean JSON from markdown if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Parse JSON with better error handling for backslash issues
            try:
                html_content = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Problematic content around error: {content[max(0, e.pos-50):e.pos+50]}")
                
                # Try to fix common backslash issues
                if "Invalid \\escape" in str(e):
                    self._log_message("agent", "Attempting to fix JSON backslash escaping issues")
                    try:
                        # Replace common problematic patterns
                        fixed_content = self._fix_json_escaping(content)
                        html_content = json.loads(fixed_content)
                        self._log_message("agent", "Successfully fixed JSON escaping issues")
                    except Exception as fix_error:
                        logger.error(f"Could not fix JSON escaping: {fix_error}")
                        raise e
                else:
                    raise e
            
            # Validate required fields
            required_fields = ['title', 'description', 'main_content', 'custom_css', 'custom_js']
            for field in required_fields:
                if field not in html_content:
                    html_content[field] = ""
            
            self._log_message("agent", "Generated final HTML content")
            
            # Validate and fix HTML/JavaScript issues
            validation_result = self._validate_and_fix_html(html_content)
            if validation_result.get("content_fixed"):
                html_content = validation_result["html_content"]
                self._log_message("agent", f"Applied validation fixes: {validation_result.get('message', 'Content improved')}")
            
            # Validate URLs in generated content
            url_validation_result = self._validate_generated_urls(html_content)
            
            # If we have invalid URLs and haven't exceeded LLM call limit, try to fix them
            if (url_validation_result.get("has_invalid_urls") and 
                self.llm_calls_made < self.max_llm_calls):
                
                self._log_message("agent", f"Found {len(url_validation_result.get('invalid_urls', []))} invalid URLs, attempting to fix")
                fixed_html = self._fix_invalid_urls(html_content, url_validation_result)
                if fixed_html:
                    html_content = fixed_html
                    self._log_message("agent", "Applied URL fixes to generated content")
            
            return {
                "success": True,
                "html_content": html_content,
                "intelligence_used": len(self.context["tool_results"]),
                "iterations_completed": self.iterations_completed,
                "llm_calls_made": self.llm_calls_made,
                "html_validation": validation_result,
                "url_validation": url_validation_result,
                "context": self.context
            }
            
        except Exception as e:
            logger.error(f"Final HTML generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "context": self.context
            }
    
    def _build_intelligence_summary(self) -> str:
        """Build a comprehensive summary of all gathered intelligence"""
        summary_parts = ["RESEARCH FINDINGS:"]
        
        for i, result in enumerate(self.context["tool_results"], 1):
            action = result["action"]
            tool_result = result["result"]
            action_name = action.get("action", "Unknown")
            
            summary_parts.append(f"\n{i}. {action_name.upper()}:")
            
            if tool_result.get("success"):
                if action_name == "web_search":
                    query = action.get("parameters", {}).get("query", "")
                    results = tool_result.get("results", [])
                    summary_parts.append(f"   Query: {query}")
                    summary_parts.append(f"   Found {len(results)} current results:")
                    for j, r in enumerate(results[:3], 1):
                        summary_parts.append(f"   {j}. {r.get('title', '')}")
                        summary_parts.append(f"      {r.get('description', '')[:100]}...")
                        summary_parts.append(f"      Source: {r.get('url', '')}")
                
                elif action_name == "fetch_stac_sample_data":
                    collection = tool_result.get("collection", "")
                    total = tool_result.get("total_found", 0)
                    props = tool_result.get("available_properties", [])
                    summary_parts.append(f"   Collection: {collection}")
                    summary_parts.append(f"   Found {total} data items")
                    summary_parts.append(f"   Available properties: {', '.join(props[:10])}")
                
                elif action_name == "validate_api_endpoint":
                    url = tool_result.get("url", "")
                    accessible = tool_result.get("is_accessible", False)
                    status = tool_result.get("status_code", "unknown")
                    summary_parts.append(f"   URL: {url}")
                    summary_parts.append(f"   Status: {status} ({'accessible' if accessible else 'not accessible'})")
            else:
                error = tool_result.get("error", "Unknown error")
                summary_parts.append(f"   FAILED: {error}")
        
        if not self.context["tool_results"]:
            summary_parts.append("No additional research conducted.")
        
        return "\n".join(summary_parts)
    
    def _fix_json_escaping(self, content: str) -> str:
        """Fix common JSON escaping issues in LLM-generated content"""
        import re
        
        # Common problematic patterns in JavaScript that break JSON
        fixes = [
            # Fix unescaped backslashes in regex patterns
            (r'\\s\+', r'\\\\s\\+'),  # \s+ -> \\s\\+
            (r'\\w\+', r'\\\\w\\+'),  # \w+ -> \\w\\+
            (r'\\d\+', r'\\\\d\\+'),  # \d+ -> \\d\\+
            (r'\\n', r'\\\\n'),        # \n -> \\n
            (r'\\t', r'\\\\t'),        # \t -> \\t
            (r'\\r', r'\\\\r'),        # \r -> \\r
            
            # Fix unescaped backslashes in URLs and paths
            (r'([^\\])\\([^\\"])', r'\1\\\\\\2'),  # Single backslash -> double backslash
        ]
        
        fixed_content = content
        for pattern, replacement in fixes:
            fixed_content = re.sub(pattern, replacement, fixed_content)
        
        return fixed_content
    
    def _validate_and_fix_html(self, html_content: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and potentially fix HTML/JavaScript issues"""
        try:
            from .validation_agent import ValidationAgent
            
            validator = ValidationAgent()
            result = validator.validate_and_fix(html_content)
            
            return result
            
        except Exception as e:
            logger.error(f"HTML validation failed: {e}")
            return {
                "success": False,
                "content_fixed": False,
                "html_content": html_content,
                "error": str(e)
            }
    
    def _validate_generated_urls(self, html_content: Dict[str, Any]) -> Dict[str, Any]:
        """Validate URLs in generated HTML content using ValidateHTMLEndpointsTool"""
        try:
            # Get the validation tool
            tools = tool_registry.get_available_tools()
            validate_tool = tools.get("validate_html_endpoints")
            
            if not validate_tool:
                logger.warning("ValidateHTMLEndpointsTool not available")
                return {
                    "success": False,
                    "error": "Validation tool not available",
                    "has_invalid_urls": False
                }
            
            # Combine all HTML content for validation
            combined_content = ""
            if html_content.get("main_content"):
                combined_content += html_content["main_content"] + "\n"
            if html_content.get("custom_js"):
                combined_content += "<script>" + html_content["custom_js"] + "</script>\n"
            if html_content.get("custom_css"):
                combined_content += "<style>" + html_content["custom_css"] + "</style>\n"
            
            # Run validation
            validation_result = validate_tool.execute({
                "html_content": combined_content
            })
            
            self._log_message("tool", f"URL validation completed: found {len(validation_result.get('endpoints', []))} URLs")
            
            # Determine if there are invalid URLs
            invalid_urls = []
            if validation_result.get("success") and validation_result.get("endpoints"):
                for endpoint_data in validation_result["endpoints"]:
                    if not endpoint_data.get("is_accessible", True):
                        invalid_urls.append({
                            "url": endpoint_data.get("url"),
                            "status": endpoint_data.get("status_code"),
                            "error": endpoint_data.get("error_message")
                        })
            
            validation_result["has_invalid_urls"] = len(invalid_urls) > 0
            validation_result["invalid_urls"] = invalid_urls
            
            return validation_result
            
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "has_invalid_urls": False
            }
    
    def _fix_invalid_urls(self, html_content: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to fix invalid URLs by asking the LLM to regenerate with specific feedback"""
        if not self.client or not validation_result.get("invalid_urls"):
            return None
        
        try:
            # Build specific feedback about invalid URLs
            invalid_urls_info = []
            for invalid in validation_result["invalid_urls"]:
                url_info = f"❌ {invalid['url']}"
                if invalid.get('status'):
                    url_info += f" (Status: {invalid['status']})"
                if invalid.get('error'):
                    url_info += f" - {invalid['error']}"
                invalid_urls_info.append(url_info)
            
            # Get intelligence about valid URLs from our research
            valid_urls_from_research = []
            for result in self.context["tool_results"]:
                tool_result = result["result"]
                if tool_result.get("success"):
                    # Extract valid URLs from STAC data results
                    if "base_url" in tool_result and tool_result.get("is_accessible"):
                        valid_urls_from_research.append(f"✅ {tool_result['base_url']} - Validated STAC endpoint")
                    # Extract valid URLs from API validation results
                    elif "url" in tool_result and tool_result.get("is_accessible"):
                        valid_urls_from_research.append(f"✅ {tool_result['url']} - Validated API endpoint")
            
            system_prompt = """
            You are fixing invalid URLs in disaster response application code. The user has provided you with:
            1. HTML content that contains invalid/inaccessible URLs
            2. A list of the specific URLs that are failing
            3. A list of valid URLs that were confirmed during research
            
            Your task:
            - Replace invalid URLs with valid alternatives from the research
            - Remove or comment out API calls that can't be fixed
            - Add proper error handling and fallback messages
            - Keep all other content exactly the same
            
            Return ONLY the corrected JSON with the same structure (title, description, main_content, custom_css, custom_js).
            """
            
            user_prompt = f"""
            INVALID URLs DETECTED:
            {chr(10).join(invalid_urls_info)}
            
            VALID URLs FROM RESEARCH:
            {chr(10).join(valid_urls_from_research) if valid_urls_from_research else "No confirmed valid URLs found in research"}
            
            CURRENT HTML CONTENT TO FIX:
            {json.dumps(html_content, indent=2)}
            
            Please fix the invalid URLs by:
            1. Replacing them with valid alternatives from research if available
            2. Adding proper error handling with try/catch blocks
            3. Including fallback messages like "Data source temporarily unavailable"
            4. Commenting out or removing calls that cannot be fixed
            
            Keep the title, description, and overall structure identical. Only fix the URL issues.
            """
            
            self.llm_calls_made += 1
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more precise fixes
                max_tokens=getattr(settings, 'AGENT_MAX_TOKENS_FINAL_GENERATION', 6000)
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean JSON from markdown if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Parse JSON with error handling
            try:
                fixed_html = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in URL fixing: {e}")
                # If JSON parsing fails, return None to indicate fix failed
                return None
            
            # Validate that we still have the required structure
            required_fields = ['title', 'description', 'main_content', 'custom_css', 'custom_js']
            for field in required_fields:
                if field not in fixed_html:
                    fixed_html[field] = html_content.get(field, "")
            
            return fixed_html
            
        except Exception as e:
            logger.error(f"URL fixing failed: {e}")
            return None