"""
Validation Agent for HTML/JavaScript quality assurance
"""
import json
import logging
from typing import Dict, List, Any, Optional
from django.conf import settings
from .validation_tools import ValidationOrchestrator

# OpenAI import handling
try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    openai_available = False

logger = logging.getLogger(__name__)


class ValidationAgent:
    """Agent that validates and fixes generated HTML/JavaScript content"""
    
    def __init__(self):
        self.client = None
        if openai_available and settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        self.validator = ValidationOrchestrator()
        self.max_fix_attempts = 2
    
    def validate_and_fix(self, html_content: Dict[str, str]) -> Dict[str, Any]:
        """
        Main method: validate content and attempt fixes if needed
        
        Args:
            html_content: Dict with keys like 'title', 'description', 'main_content', 'custom_css', 'custom_js'
        
        Returns:
            Dict with validation results and potentially fixed content
        """
        
        # Step 1: Initial validation
        validation_result = self.validator.validate_generated_content(html_content)
        
        if not validation_result["needs_fixing"]:
            return {
                "success": True,
                "content_fixed": False,
                "html_content": html_content,
                "validation_result": validation_result,
                "message": "Content passed all validations"
            }
        
        logger.info(f"Found {validation_result['total_issues']} issues, attempting fixes")
        
        # Step 2: Attempt to fix issues
        if self.client:
            fixed_content = self._attempt_fixes(html_content, validation_result)
            
            if fixed_content:
                # Step 3: Re-validate fixed content
                revalidation_result = self.validator.validate_generated_content(fixed_content)
                
                return {
                    "success": True,
                    "content_fixed": True,
                    "html_content": fixed_content,
                    "original_validation": validation_result,
                    "final_validation": revalidation_result,
                    "improvements": self._calculate_improvements(validation_result, revalidation_result),
                    "message": f"Fixed {validation_result['total_issues'] - revalidation_result['total_issues']} issues"
                }
        
        # Could not fix or no LLM available
        return {
            "success": True,
            "content_fixed": False,
            "html_content": html_content,
            "validation_result": validation_result,
            "message": f"Found {validation_result['total_issues']} issues but could not auto-fix"
        }
    
    def _attempt_fixes(self, html_content: Dict[str, str], validation_result: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Attempt to fix identified issues using LLM"""
        
        for attempt in range(self.max_fix_attempts):
            try:
                fixed_content = self._generate_fixes(html_content, validation_result, attempt + 1)
                
                if fixed_content:
                    # Quick validation to see if we made progress
                    quick_validation = self.validator.validate_generated_content(fixed_content)
                    if quick_validation["total_issues"] < validation_result["total_issues"]:
                        return fixed_content
                    else:
                        # Update validation result for next attempt
                        validation_result = quick_validation
                        html_content = fixed_content
                
            except Exception as e:
                logger.error(f"Fix attempt {attempt + 1} failed: {e}")
                continue
        
        return None
    
    def _generate_fixes(self, html_content: Dict[str, str], validation_result: Dict[str, Any], attempt: int) -> Optional[Dict[str, str]]:
        """Use LLM to generate fixes for identified issues"""
        
        if not self.client:
            return None
        
        # Build context about issues
        issues_context = self._build_issues_context(validation_result)
        
        system_prompt = f"""
        You are an expert HTML/JavaScript validator and fixer. You receive code with identified issues and must fix them while preserving the original functionality and intent.

        CRITICAL RULES:
        1. Fix ONLY the specific issues mentioned - don't change working code
        2. Maintain the exact same JSON structure in your response
        3. Preserve all working functionality and styling
        4. Libraries are PRE-LOADED: Leaflet, Chart.js, Bootstrap, Font Awesome
        5. Don't add <script> or <link> tags for pre-loaded libraries
        
        COMMON FIXES:
        - Add missing HTML elements (divs with IDs, canvas elements)
        - Fix JavaScript syntax errors (missing semicolons, braces)
        - Ensure element IDs match JavaScript references
        - Remove duplicate library imports
        - Fix unclosed HTML tags
        
        Return the EXACT same JSON structure with fixes applied:
        {{
          "title": "...",
          "description": "...",
          "main_content": "...",
          "custom_css": "...", 
          "custom_js": "..."
        }}
        """
        
        user_prompt = f"""
        Fix the following issues in this HTML/JavaScript content:

        ISSUES TO FIX (Attempt {attempt}):
        {issues_context}

        CURRENT CONTENT:
        {json.dumps(html_content, indent=2)}

        Please fix these specific issues while keeping everything else exactly the same. Focus on the most critical issues first.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for precise fixes
                max_tokens=getattr(settings, 'AGENT_MAX_TOKENS_FINAL_GENERATION', 6000)
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean JSON from markdown if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            fixed_content = json.loads(content)
            
            # Validate that we still have the required structure
            required_fields = ['title', 'description', 'main_content', 'custom_css', 'custom_js']
            for field in required_fields:
                if field not in fixed_content:
                    fixed_content[field] = html_content.get(field, "")
            
            return fixed_content
            
        except Exception as e:
            logger.error(f"Fix generation failed: {e}")
            return None
    
    def _build_issues_context(self, validation_result: Dict[str, Any]) -> str:
        """Build a context string describing the issues found"""
        context_parts = []
        
        if validation_result["total_issues"] == 0:
            return "No issues found."
        
        context_parts.append(f"Found {validation_result['total_issues']} issues (Severity: {validation_result['overall_severity']}):")
        context_parts.append("")
        
        # Group issues by type
        detailed_results = validation_result.get("detailed_results", {})
        
        html_issues = detailed_results.get("html_validation", {}).get("issues", [])
        if html_issues:
            context_parts.append("HTML STRUCTURE ISSUES:")
            for issue in html_issues[:5]:  # Limit to top 5
                context_parts.append(f"  • {issue}")
            context_parts.append("")
        
        js_issues = detailed_results.get("js_validation", {}).get("issues", [])
        if js_issues:
            context_parts.append("JAVASCRIPT ISSUES:")
            for issue in js_issues[:5]:  # Limit to top 5
                context_parts.append(f"  • {issue}")
            context_parts.append("")
        
        dep_issues = detailed_results.get("dependency_validation", {}).get("issues", [])
        if dep_issues:
            context_parts.append("DEPENDENCY ISSUES:")
            for issue in dep_issues[:5]:  # Limit to top 5
                context_parts.append(f"  • {issue}")
            context_parts.append("")
        
        # Add suggestions
        suggestions = validation_result.get("suggestions", [])
        if suggestions:
            context_parts.append("SUGGESTED FIXES:")
            for suggestion in suggestions[:10]:  # Limit to top 10
                context_parts.append(f"  → {suggestion}")
        
        return "\n".join(context_parts)
    
    def _calculate_improvements(self, original: Dict[str, Any], final: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate what improvements were made"""
        return {
            "issues_fixed": original["total_issues"] - final["total_issues"],
            "original_issues": original["total_issues"],
            "remaining_issues": final["total_issues"],
            "severity_improved": original["overall_severity"] != final["overall_severity"],
            "original_severity": original["overall_severity"],
            "final_severity": final["overall_severity"]
        }
    
    def validate_only(self, html_content: Dict[str, str]) -> Dict[str, Any]:
        """Just validate content without attempting fixes"""
        validation_result = self.validator.validate_generated_content(html_content)
        
        return {
            "success": True,
            "validation_result": validation_result,
            "needs_fixing": validation_result["needs_fixing"]
        }