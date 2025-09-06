"""
Validation tools for HTML/JavaScript quality assurance
"""
import re
import json
import html
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class HTMLStructureValidator:
    """Validates HTML structure and common issues"""
    
    def validate(self, html_content: str) -> Dict[str, Any]:
        """Validate HTML structure and return issues found"""
        issues = []
        suggestions = []
        
        try:
            # Check for basic HTML structure
            if not re.search(r'<html[^>]*>', html_content, re.IGNORECASE):
                issues.append("Missing <html> tag")
                suggestions.append("Add proper HTML document structure")
            
            if not re.search(r'<head[^>]*>.*?</head>', html_content, re.DOTALL | re.IGNORECASE):
                issues.append("Missing or empty <head> section")
                suggestions.append("Add <head> with meta tags and title")
            
            if not re.search(r'<body[^>]*>.*?</body>', html_content, re.DOTALL | re.IGNORECASE):
                issues.append("Missing or empty <body> section")
                suggestions.append("Add <body> with content")
            
            # Check for common element ID requirements
            map_elements = re.findall(r'L\.map\([\'"]([^\'"]+)[\'"]', html_content)
            for map_id in map_elements:
                if not re.search(f'id=[\'"]?{re.escape(map_id)}[\'"]?', html_content):
                    issues.append(f"Leaflet map references element '{map_id}' but no element with that ID exists")
                    suggestions.append(f"Add <div id='{map_id}'></div> for the map")
            
            # Check for Chart.js canvas requirements
            chart_elements = re.findall(r'getElementById\([\'"]([^\'"]+)[\'"].*?getContext\([\'"]2d[\'"]', html_content)
            for chart_id in chart_elements:
                if not re.search(f'<canvas[^>]*id=[\'"]?{re.escape(chart_id)}[\'"]?', html_content):
                    issues.append(f"Chart.js references canvas '{chart_id}' but no canvas element with that ID exists")
                    suggestions.append(f"Add <canvas id='{chart_id}'></canvas> for the chart")
            
            # Check for Bootstrap container structure
            if 'class=' in html_content and 'bootstrap' in html_content.lower():
                if not re.search(r'class=[\'"][^\'"]*(container|container-fluid)[^\'"]', html_content):
                    issues.append("Using Bootstrap but missing container structure")
                    suggestions.append("Wrap content in Bootstrap container: <div class='container'>")
            
            # Check for unclosed tags (basic check)
            unclosed = self._find_unclosed_tags(html_content)
            if unclosed:
                issues.extend([f"Potentially unclosed tag: {tag}" for tag in unclosed])
                suggestions.extend([f"Ensure {tag} tags are properly closed" for tag in unclosed])
            
            return {
                "success": True,
                "issues": issues,
                "suggestions": suggestions,
                "severity": "high" if len(issues) > 3 else "medium" if issues else "low"
            }
            
        except Exception as e:
            logger.error(f"HTML validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "issues": ["HTML validation failed"],
                "suggestions": ["Check HTML syntax manually"]
            }
    
    def _find_unclosed_tags(self, html: str) -> List[str]:
        """Basic check for potentially unclosed tags"""
        # This is a simplified check - a full parser would be more accurate
        tag_pattern = r'<(/?)(\w+)[^>]*>'
        tags = re.findall(tag_pattern, html, re.IGNORECASE)
        
        stack = []
        unclosed = []
        
        for is_closing, tag_name in tags:
            tag_name = tag_name.lower()
            
            # Skip self-closing tags
            if tag_name in ['img', 'br', 'hr', 'meta', 'link', 'input']:
                continue
                
            if is_closing:  # Closing tag
                if stack and stack[-1] == tag_name:
                    stack.pop()
                else:
                    # Mismatched closing tag
                    if tag_name not in unclosed:
                        unclosed.append(tag_name)
            else:  # Opening tag
                stack.append(tag_name)
        
        # Tags left in stack are potentially unclosed
        unclosed.extend(stack)
        return list(set(unclosed))


class JavaScriptValidator:
    """Validates JavaScript syntax and library usage"""
    
    def validate(self, js_content: str) -> Dict[str, Any]:
        """Validate JavaScript code for common issues"""
        issues = []
        suggestions = []
        
        try:
            # Check for syntax errors (basic checks)
            syntax_issues = self._check_basic_syntax(js_content)
            issues.extend(syntax_issues)
            
            # Check library usage
            library_issues = self._check_library_usage(js_content)
            issues.extend(library_issues["issues"])
            suggestions.extend(library_issues["suggestions"])
            
            # Check for common errors
            common_issues = self._check_common_errors(js_content)
            issues.extend(common_issues)
            
            return {
                "success": True,
                "issues": issues,
                "suggestions": suggestions,
                "severity": "high" if len(issues) > 2 else "medium" if issues else "low"
            }
            
        except Exception as e:
            logger.error(f"JavaScript validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "issues": ["JavaScript validation failed"],
                "suggestions": ["Check JavaScript syntax manually"]
            }
    
    def _check_basic_syntax(self, js: str) -> List[str]:
        """Check for basic JavaScript syntax issues"""
        issues = []
        
        # Check for unmatched braces/brackets
        braces = js.count('{') - js.count('}')
        brackets = js.count('[') - js.count(']')
        parens = js.count('(') - js.count(')')
        
        if braces != 0:
            issues.append(f"Unmatched braces: {abs(braces)} {'opening' if braces > 0 else 'closing'} braces")
        if brackets != 0:
            issues.append(f"Unmatched brackets: {abs(brackets)} {'opening' if brackets > 0 else 'closing'} brackets")
        if parens != 0:
            issues.append(f"Unmatched parentheses: {abs(parens)} {'opening' if parens > 0 else 'closing'} parentheses")
        
        # Check for missing semicolons at line ends (basic check)
        lines = js.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.endswith((';', '{', '}', ')', ']')) and not line.startswith(('*', '//', '/*')):
                if re.search(r'(var|let|const|return)\s+', line) and not line.endswith(';'):
                    issues.append(f"Line {i}: Possible missing semicolon")
        
        return issues
    
    def _check_library_usage(self, js: str) -> Dict[str, Any]:
        """Check for proper library usage"""
        issues = []
        suggestions = []
        
        # Check Leaflet usage
        if 'L.' in js:
            # Good usage patterns
            if re.search(r'L\.map\s*\(\s*[\'"][^\'"]+[\'"]', js):
                # Check if using proper element ID
                map_calls = re.findall(r'L\.map\s*\(\s*[\'"]([^\'"]+)[\'"]', js)
                for map_id in map_calls:
                    suggestions.append(f"Ensure element with ID '{map_id}' exists for Leaflet map")
        
        # Check Chart.js usage
        if 'new Chart' in js:
            # Check for proper context setup
            if not re.search(r'getContext\s*\(\s*[\'"]2d[\'"]', js):
                issues.append("Chart.js usage found but missing canvas context setup")
                suggestions.append("Add: const ctx = document.getElementById('chartId').getContext('2d');")
        
        # Check for jQuery usage (shouldn't be needed with our templates)
        if '$(' in js or 'jQuery' in js:
            issues.append("jQuery usage detected - Bootstrap and vanilla JS should be sufficient")
            suggestions.append("Use vanilla JavaScript or Bootstrap JS instead of jQuery")
        
        # Check for duplicate library imports
        if '<script' in js and any(lib in js for lib in ['leaflet', 'chart.js', 'bootstrap']):
            issues.append("Attempting to load libraries that are already pre-loaded")
            suggestions.append("Remove <script> tags - libraries are already loaded in templates")
        
        return {"issues": issues, "suggestions": suggestions}
    
    def _check_common_errors(self, js: str) -> List[str]:
        """Check for common JavaScript errors"""
        issues = []
        
        # Check for undefined variables (basic check)
        if re.search(r'\bconsole\.log\s*\(\s*[^)]*undefined[^)]*\)', js):
            issues.append("Logging undefined variables detected")
        
        # Check for fetch without error handling
        fetch_calls = re.findall(r'fetch\s*\([^)]+\)', js)
        for fetch_call in fetch_calls:
            # Look for .catch or try/catch around this fetch
            # This is a simplified check
            if '.catch' not in js and 'try' not in js:
                issues.append("fetch() calls without error handling detected")
                break
        
        return issues


class DependencyChecker:
    """Checks for dependency conflicts and missing requirements"""
    
    def validate(self, html_content: str, css_content: str = "", js_content: str = "") -> Dict[str, Any]:
        """Check dependencies across HTML, CSS, and JS"""
        issues = []
        suggestions = []
        
        try:
            full_content = html_content + css_content + js_content
            
            # Check for duplicate library imports
            library_imports = self._find_library_imports(full_content)
            duplicates = self._find_duplicates(library_imports)
            
            if duplicates:
                for lib in duplicates:
                    issues.append(f"Duplicate import of {lib} detected")
                    suggestions.append(f"Remove duplicate {lib} imports - library is pre-loaded")
            
            # Check for missing element references
            element_refs = self._find_element_references(js_content)
            missing_elements = self._check_missing_elements(element_refs, html_content)
            
            for element_id in missing_elements:
                issues.append(f"JavaScript references element '{element_id}' but element not found in HTML")
                suggestions.append(f"Add element with id='{element_id}' to HTML")
            
            # Check for CSS class usage without Bootstrap
            if self._uses_bootstrap_classes(html_content) and not self._has_bootstrap(full_content):
                issues.append("Bootstrap CSS classes used but Bootstrap not detected")
                suggestions.append("Bootstrap is pre-loaded - ensure template is being used correctly")
            
            return {
                "success": True,
                "issues": issues,
                "suggestions": suggestions,
                "library_imports": library_imports,
                "severity": "high" if len(issues) > 2 else "medium" if issues else "low"
            }
            
        except Exception as e:
            logger.error(f"Dependency validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "issues": ["Dependency validation failed"],
                "suggestions": ["Check dependencies manually"]
            }
    
    def _find_library_imports(self, content: str) -> List[str]:
        """Find all library imports in content"""
        imports = []
        
        # Script tags
        script_tags = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', content, re.IGNORECASE)
        imports.extend(script_tags)
        
        # Link tags
        link_tags = re.findall(r'<link[^>]*href=[\'"]([^\'"]+)[\'"]', content, re.IGNORECASE)
        imports.extend(link_tags)
        
        return imports
    
    def _find_duplicates(self, imports: List[str]) -> List[str]:
        """Find duplicate library imports"""
        seen = set()
        duplicates = []
        
        for import_url in imports:
            # Extract library name from URL
            lib_name = self._extract_library_name(import_url)
            if lib_name:
                if lib_name in seen:
                    duplicates.append(lib_name)
                else:
                    seen.add(lib_name)
        
        return duplicates
    
    def _extract_library_name(self, url: str) -> Optional[str]:
        """Extract library name from URL"""
        url_lower = url.lower()
        if 'leaflet' in url_lower:
            return 'Leaflet'
        elif 'chart' in url_lower:
            return 'Chart.js'
        elif 'bootstrap' in url_lower:
            return 'Bootstrap'
        elif 'font-awesome' in url_lower or 'fontawesome' in url_lower:
            return 'Font Awesome'
        return None
    
    def _find_element_references(self, js: str) -> List[str]:
        """Find element IDs referenced in JavaScript"""
        ids = []
        
        # getElementById calls
        get_by_id = re.findall(r'getElementById\s*\(\s*[\'"]([^\'"]+)[\'"]', js)
        ids.extend(get_by_id)
        
        # Leaflet map calls
        map_ids = re.findall(r'L\.map\s*\(\s*[\'"]([^\'"]+)[\'"]', js)
        ids.extend(map_ids)
        
        # Query selector with IDs
        query_ids = re.findall(r'querySelector\s*\(\s*[\'"]#([^\'"]+)[\'"]', js)
        ids.extend(query_ids)
        
        return list(set(ids))
    
    def _check_missing_elements(self, element_ids: List[str], html: str) -> List[str]:
        """Check which element IDs are missing from HTML"""
        missing = []
        
        for element_id in element_ids:
            if not re.search(f'id=[\'"]?{re.escape(element_id)}[\'"]?', html):
                missing.append(element_id)
        
        return missing
    
    def _uses_bootstrap_classes(self, html: str) -> bool:
        """Check if HTML uses Bootstrap CSS classes"""
        bootstrap_classes = ['container', 'row', 'col-', 'btn', 'card', 'navbar', 'alert', 'modal']
        return any(cls in html for cls in bootstrap_classes)
    
    def _has_bootstrap(self, content: str) -> bool:
        """Check if Bootstrap is loaded"""
        return 'bootstrap' in content.lower()


class ValidationOrchestrator:
    """Orchestrates all validation tools"""
    
    def __init__(self):
        self.html_validator = HTMLStructureValidator()
        self.js_validator = JavaScriptValidator()
        self.dependency_checker = DependencyChecker()
    
    def validate_generated_content(self, html_content: Dict[str, str]) -> Dict[str, Any]:
        """Run all validations on generated content"""
        
        # Extract content parts
        main_content = html_content.get('main_content', '')
        custom_css = html_content.get('custom_css', '')
        custom_js = html_content.get('custom_js', '')
        title = html_content.get('title', '')
        description = html_content.get('description', '')
        
        # Combine full HTML for validation
        full_html = f"""
        <html>
        <head>
            <title>{title}</title>
            <style>{custom_css}</style>
        </head>
        <body>
            {main_content}
            <script>{custom_js}</script>
        </body>
        </html>
        """
        
        results = {
            "html_validation": self.html_validator.validate(full_html),
            "js_validation": self.js_validator.validate(custom_js),
            "dependency_validation": self.dependency_checker.validate(full_html, custom_css, custom_js)
        }
        
        # Aggregate results
        all_issues = []
        all_suggestions = []
        max_severity = "low"
        
        for validation_type, result in results.items():
            if result.get("success"):
                all_issues.extend(result.get("issues", []))
                all_suggestions.extend(result.get("suggestions", []))
                
                severity = result.get("severity", "low")
                if severity == "high" or (severity == "medium" and max_severity == "low"):
                    max_severity = severity
        
        return {
            "success": True,
            "overall_severity": max_severity,
            "total_issues": len(all_issues),
            "issues": all_issues,
            "suggestions": all_suggestions,
            "detailed_results": results,
            "needs_fixing": len(all_issues) > 0
        }