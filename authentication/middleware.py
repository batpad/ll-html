from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponse
from django.template import Template, Context
from .models import UserWhitelistStatus


class WhitelistMiddleware:
    """Middleware to enforce whitelist checking for authenticated users"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that don't require authentication - use string patterns to avoid issues
        self.exempt_urls = [
            '/accounts/',
            '/admin/',
        ]

    def __call__(self, request):
        # Skip middleware for exempt URLs
        if any(request.path.startswith(url) for url in self.exempt_urls):
            response = self.get_response(request)
            return response
        
        # Skip for unauthenticated users - redirect to login
        if not request.user.is_authenticated:
            return redirect('/accounts/login/')
        
        # For superusers, skip whitelist checking
        if request.user.is_superuser:
            response = self.get_response(request)
            return response
        
        # Check whitelist status
        try:
            status = UserWhitelistStatus.objects.get(user=request.user)
        except UserWhitelistStatus.DoesNotExist:
            # For new users, check if we have GitHub data in session
            github_username = request.session.get('github_username', '')
            github_orgs = request.session.get('github_orgs', [])
            
            # Create status for first-time user
            status = UserWhitelistStatus.update_user_status(
                request.user, 
                github_username, 
                github_orgs
            )
            
            # Clear session data
            request.session.pop('github_username', None)
            request.session.pop('github_orgs', None)
        
        # If not whitelisted, show access denied
        if not status.is_whitelisted:
            return self.access_denied_response(request)
        
        response = self.get_response(request)
        return response
    
    def access_denied_response(self, request):
        """Return access denied response"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Access Denied</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 600px; 
                    margin: 50px auto; 
                    padding: 20px;
                    text-align: center;
                }
                .error-box {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 30px;
                    margin: 20px 0;
                }
                .logout-btn {
                    background-color: #dc3545;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="error-box">
                <h1>🚫 Access Denied</h1>
                <p>Your GitHub account is not authorized to access this application.</p>
                <p>Please contact your administrator to request access or check if your GitHub organization is whitelisted.</p>
                <a href="/accounts/logout/" class="logout-btn">Logout</a>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_content)
        context = Context({'user': request.user})
        rendered_html = template.render(context)
        
        return HttpResponse(rendered_html, status=403)