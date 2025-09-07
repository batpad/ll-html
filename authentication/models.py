from django.db import models
from django.contrib.auth.models import User
import requests
from django.conf import settings


class WhitelistedOrganization(models.Model):
    """Model for whitelisted GitHub organizations"""
    organization = models.CharField(
        max_length=255,
        unique=True,
        help_text="GitHub organization name (e.g., 'mycompany', 'opensource-org')"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional description for this organization"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this organization is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['organization']
        verbose_name = "Whitelisted GitHub Organization"
        verbose_name_plural = "Whitelisted GitHub Organizations"

    def __str__(self):
        return f"@{self.organization}"

    def clean(self):
        if self.organization:
            self.organization = self.organization.lower().strip()
            if self.organization.startswith('@'):
                self.organization = self.organization[1:]


class WhitelistedUsername(models.Model):
    """Model for individually whitelisted GitHub usernames"""
    username = models.CharField(
        max_length=255,
        unique=True,
        help_text="GitHub username (e.g., 'johndoe')"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional description for this username"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this username is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['username']
        verbose_name = "Whitelisted GitHub Username"
        verbose_name_plural = "Whitelisted GitHub Usernames"

    def __str__(self):
        return f"@{self.username}"

    def clean(self):
        if self.username:
            self.username = self.username.lower().strip()
            if self.username.startswith('@'):
                self.username = self.username[1:]


class UserWhitelistStatus(models.Model):
    """Track whitelist status for GitHub users"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='whitelist_status'
    )
    github_username = models.CharField(max_length=255, blank=True)
    github_organizations = models.JSONField(default=list, blank=True)
    is_whitelisted = models.BooleanField(default=False)
    whitelist_reason = models.CharField(
        max_length=50,
        choices=[
            ('organization', 'Whitelisted Organization'),
            ('username', 'Whitelisted Username'),
            ('manual', 'Manual Override'),
        ],
        null=True,
        blank=True
    )
    last_checked = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Whitelist Status"
        verbose_name_plural = "User Whitelist Statuses"

    def __str__(self):
        status = "✓ Whitelisted" if self.is_whitelisted else "✗ Not Whitelisted"
        username = self.github_username or self.user.email
        return f"{username} - {status}"

    @classmethod
    def check_user_whitelist(cls, user, github_username=None, github_orgs=None):
        """Check if a user should be whitelisted based on GitHub data"""
        if not github_username:
            return False, None
        
        # Check individual username whitelist
        if WhitelistedUsername.objects.filter(username=github_username.lower(), is_active=True).exists():
            return True, 'username'
        
        # Check organization whitelist
        if github_orgs:
            for org in github_orgs:
                if WhitelistedOrganization.objects.filter(organization=org.lower(), is_active=True).exists():
                    return True, 'organization'
        
        return False, None

    @classmethod
    def update_user_status(cls, user, github_username=None, github_orgs=None):
        """Update or create whitelist status for a GitHub user"""
        is_whitelisted, reason = cls.check_user_whitelist(user, github_username, github_orgs)
        
        status, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'github_username': github_username or '',
                'github_organizations': github_orgs or [],
                'is_whitelisted': is_whitelisted,
                'whitelist_reason': reason
            }
        )
        
        if not created:
            status.github_username = github_username or ''
            status.github_organizations = github_orgs or []
            status.is_whitelisted = is_whitelisted
            status.whitelist_reason = reason
            status.save()
        
        return status

    @classmethod
    def get_github_organizations(cls, access_token):
        """Fetch user's GitHub organizations using access token"""
        try:
            headers = {'Authorization': f'token {access_token}'}
            response = requests.get('https://api.github.com/user/orgs', headers=headers)
            
            if response.status_code == 200:
                orgs = response.json()
                return [org['login'] for org in orgs]
            return []
        except Exception:
            return []
