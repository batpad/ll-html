# Deployment Guide

This guide walks you through deploying the ll-html Django application on Ubuntu 24.04 with nginx + gunicorn.

## Prerequisites

- Fresh Ubuntu 24.04 VPS
- Domain `llhtml.whydidweevendothis.com` pointing to your server's IP
- Root or sudo access

## Quick Setup

1. **Upload your code to the server:**
   ```bash
   # Option 1: Clone from git (update the URL in deploy/setup.sh first)
   # Option 2: Upload manually to /opt/ll-html
   scp -r . user@your-server:/opt/ll-html/
   ```

2. **Run the setup script:**
   ```bash
   cd /opt/ll-html
   sudo ./deploy/setup.sh
   ```

3. **Configure environment variables:**
   ```bash
   sudo nano /opt/ll-html/.env
   ```
   Update the following required values:
   - `SECRET_KEY`: Generate a new Django secret key
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `GITHUB_CLIENT_ID` & `GITHUB_CLIENT_SECRET`: For GitHub OAuth

4. **Restart services:**
   ```bash
   sudo systemctl restart ll-html nginx
   ```

## Manual Setup Steps

If you prefer manual setup or the script fails:

### 1. System Setup
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx git curl ufw certbot python3-certbot-nginx
```

### 2. Application Setup
```bash
sudo mkdir -p /opt/ll-html /var/log/ll-html
sudo chown -R www-data:www-data /opt/ll-html /var/log/ll-html
cd /opt/ll-html

# Copy your code here or clone from git
sudo -u www-data python3 -m venv venv
sudo -u www-data ./venv/bin/pip install -r requirements.txt

# Environment setup
sudo -u www-data cp deploy/production.env.example .env
# Edit .env with your actual values

# Django setup
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput
sudo -u www-data ./venv/bin/python manage.py migrate
sudo -u www-data ./venv/bin/python manage.py createsuperuser
```

### 3. Service Configuration
```bash
# Systemd service
sudo cp deploy/ll-html.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ll-html
sudo systemctl start ll-html

# Nginx configuration
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ll-html
sudo ln -s /etc/nginx/sites-available/ll-html /etc/nginx/sites-enabled/

# Add rate limiting to nginx.conf
sudo sed -i '/http {/a\\tlimit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;' /etc/nginx/nginx.conf

sudo nginx -t
sudo systemctl reload nginx
```

### 4. Firewall & SSL
```bash
# Firewall
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# SSL Certificate (ensure domain points to your server first)
sudo certbot --nginx -d llhtml.whydidweevendothis.com
sudo systemctl enable certbot.timer
```

## Post-Deployment

### Service Management
```bash
# Check service status
sudo systemctl status ll-html
sudo systemctl status nginx

# View logs
sudo journalctl -u ll-html -f
sudo tail -f /var/log/ll-html/gunicorn-error.log

# Restart services
sudo systemctl restart ll-html nginx
```

### Updates
```bash
cd /opt/ll-html
sudo -u www-data git pull  # if using git
sudo -u www-data ./venv/bin/pip install -r requirements.txt
sudo -u www-data ./venv/bin/python manage.py migrate
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart ll-html
```

## Configuration Files

- **Gunicorn**: `deploy/gunicorn.conf.py`
- **Nginx**: `deploy/nginx.conf`
- **Systemd**: `deploy/ll-html.service`
- **Environment**: `deploy/production.env.example`

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u ll-html -n 50
```

### 502 Bad Gateway
- Check if gunicorn is running: `sudo systemctl status ll-html`
- Check gunicorn logs: `sudo tail -f /var/log/ll-html/gunicorn-error.log`

### Static files not loading
```bash
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart nginx
```

### SSL certificate issues
```bash
sudo certbot certificates
sudo certbot renew --dry-run
```

## Security Notes

- The application runs as `www-data` user
- Firewall allows only SSH and HTTP/HTTPS
- Rate limiting is configured for API endpoints
- SSL certificates auto-renew via certbot timer
- Remember to update `ALLOWED_HOSTS` in your `.env` file

Your application will be available at `https://llhtml.whydidweevendothis.com`