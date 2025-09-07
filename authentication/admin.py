from django.contrib import admin
from django.contrib.auth.models import User
from .models import WhitelistedOrganization, WhitelistedUsername, UserWhitelistStatus


@admin.register(WhitelistedOrganization)
class WhitelistedOrganizationAdmin(admin.ModelAdmin):
    list_display = ('organization', 'description', 'is_active', 'created_at', 'created_by')
    list_filter = ('is_active', 'created_at')
    search_fields = ('organization', 'description')
    readonly_fields = ('created_at',)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(WhitelistedUsername)
class WhitelistedUsernameAdmin(admin.ModelAdmin):
    list_display = ('username', 'description', 'is_active', 'created_at', 'created_by')
    list_filter = ('is_active', 'created_at')
    search_fields = ('username', 'description')
    readonly_fields = ('created_at',)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserWhitelistStatus)
class UserWhitelistStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'github_username', 'user_email', 'is_whitelisted', 'whitelist_reason', 'last_checked')
    list_filter = ('is_whitelisted', 'whitelist_reason', 'last_checked')
    search_fields = ('user__email', 'github_username', 'user__first_name', 'user__last_name')
    readonly_fields = ('last_checked', 'created_at', 'github_organizations')
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # editing
            readonly.extend(['github_username', 'github_organizations'])
        return readonly
    
    actions = ['refresh_whitelist_status']
    
    def refresh_whitelist_status(self, request, queryset):
        updated = 0
        for status in queryset:
            # Note: This won't fetch fresh GitHub data since we don't have the access token
            # The status will be refreshed during next login
            UserWhitelistStatus.update_user_status(
                status.user, 
                status.github_username, 
                status.github_organizations
            )
            updated += 1
        
        self.message_user(
            request,
            f"Successfully refreshed whitelist status for {updated} users."
        )
    refresh_whitelist_status.short_description = "Refresh whitelist status"
