from django.dispatch import receiver
from allauth.socialaccount.signals import pre_social_login
from allauth.socialaccount.models import SocialAccount
from .models import UserWhitelistStatus
import requests


@receiver(pre_social_login)
def handle_github_login(sender, request, sociallogin, **kwargs):
    """Handle GitHub login and update user whitelist status"""
    
    if sociallogin.account.provider != 'github':
        return
    
    # Get GitHub data from the social login
    github_data = sociallogin.account.extra_data
    github_username = github_data.get('login', '')
    
    # Get access token to fetch organizations
    access_token = sociallogin.token.token if sociallogin.token else None
    github_orgs = []
    
    if access_token:
        github_orgs = UserWhitelistStatus.get_github_organizations(access_token)
    
    # If user already exists, update their status
    if sociallogin.user and sociallogin.user.id:
        UserWhitelistStatus.update_user_status(
            sociallogin.user, 
            github_username, 
            github_orgs
        )
    else:
        # For new users, we'll update after user creation
        # Store the data in the session for later use
        request.session['github_username'] = github_username
        request.session['github_orgs'] = github_orgs