# Authentication System

## Overview

This application uses **GitHub OAuth** for authentication with a **whitelist-based access control system**. Users must authenticate via GitHub and be on the approved whitelist to access the application.

## Features

- 🔐 **GitHub OAuth Authentication** - Secure login via GitHub
- 🏢 **Organization-based Whitelisting** - Allow users from specific GitHub organizations
- 👤 **Username-based Whitelisting** - Allow specific individual GitHub users
- ⚡ **Auto-sync GitHub Data** - Automatically fetches user's organizations during login
- 🛡️ **Middleware Protection** - All application views are protected by authentication
- 📊 **Admin Interface** - Easy whitelist management via Django admin

## Setup Instructions

### 1. Create GitHub OAuth App

1. Go to [GitHub Settings → Developer settings → OAuth Apps](https://github.com/settings/developers)
2. Click **"New OAuth App"**
3. Configure:
   - **Application name**: Your app name
   - **Homepage URL**: `http://localhost:8000` (for development)
   - **Authorization callback URL**: `http://localhost:8000/accounts/github/login/callback/`
4. Save the **Client ID** and **Client Secret**

### 2. Environment Configuration

Add to your `.env` file:

```bash
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
```

### 3. Database Migration

```bash
python manage.py migrate
```

### 4. Create Admin User

```bash
python manage.py createsuperuser
```

## Whitelist Management

### Via Django Admin

1. Go to `/admin/`
2. Login with superuser credentials
3. Manage whitelists under **"Authentication"** section:

#### Whitelisted GitHub Organizations
- Add organization names (e.g., `mycompany`, `facebook`, `google`)
- Any member of these organizations will be granted access
- Organizations are automatically fetched during user login

#### Whitelisted GitHub Usernames
- Add specific GitHub usernames (e.g., `johndoe`, `janedoe`)
- Individual users will be granted access regardless of their organization membership

### User Whitelist Status
- View all authenticated users and their whitelist status
- See which organizations users belong to
- Manually refresh whitelist status if needed

## How It Works

### Authentication Flow

1. **User visits protected page** → Redirected to GitHub login
2. **GitHub OAuth authentication** → User grants permissions
3. **GitHub data sync** → System fetches username and organizations
4. **Whitelist check** → Validates against whitelisted orgs/usernames
5. **Access decision** → Grant access or show denial page

### Middleware Protection

- `WhitelistMiddleware` protects all application views
- Exempt URLs: `/accounts/`, `/admin/`
- Superusers bypass whitelist checking
- Unauthenticated users redirected to login

## Required GitHub Permissions

The application requests these GitHub scopes:
- `user:email` - Access user's email address
- `read:org` - Read user's organization memberships

## Security Considerations

- 🔒 Client secrets stored in environment variables
- 🚫 Access denied page for non-whitelisted users
- 🔄 Organization data synced on each login
- 👑 Superusers always have access
- 📝 Audit trail via admin interface (who created whitelists, when)

## Troubleshooting

### Common Issues

**404 on GitHub OAuth**: Check that `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are properly set in `.env`

**Access Denied**: Verify user's GitHub username or organization is in the whitelist

**Empty Organizations**: User may have private organization membership - they need to make it public or be individually whitelisted

### Debug Commands

```bash
# Check user's whitelist status
python manage.py shell
>>> from authentication.models import UserWhitelistStatus
>>> UserWhitelistStatus.objects.all()

# Refresh all user statuses
>>> for status in UserWhitelistStatus.objects.all():
...     UserWhitelistStatus.update_user_status(status.user, status.github_username, status.github_organizations)
```

## Production Deployment

1. Update OAuth app callback URL to production domain
2. Set proper environment variables
3. Use secure secret key
4. Configure proper Django settings for production
5. Set up proper domain whitelist management process

## API Reference

### Models

- `WhitelistedOrganization` - GitHub organizations allowed access
- `WhitelistedUsername` - Individual GitHub users allowed access  
- `UserWhitelistStatus` - Tracks user whitelist status and GitHub data