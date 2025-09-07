#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting ll-html deployment setup...${NC}"

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    git \
    curl \
    ufw \
    certbot \
    python3-certbot-nginx

# Create application user (if not using www-data)
echo -e "${YELLOW}Setting up application directory...${NC}"
sudo mkdir -p /opt/ll-html
sudo mkdir -p /var/log/ll-html
sudo chown -R www-data:www-data /opt/ll-html
sudo chown -R www-data:www-data /var/log/ll-html

# Clone repository
echo -e "${YELLOW}Cloning repository...${NC}"
cd /opt
sudo -u www-data git clone https://github.com/your-username/ll-html.git ll-html || {
    echo -e "${RED}Failed to clone repository. Please update the git URL in this script.${NC}"
    echo -e "${YELLOW}Alternatively, copy your code to /opt/ll-html manually.${NC}"
}

cd /opt/ll-html

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
sudo -u www-data python3 -m venv venv

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
sudo -u www-data ./venv/bin/pip install --upgrade pip
sudo -u www-data ./venv/bin/pip install -r requirements.txt

# Copy environment file
echo -e "${YELLOW}Setting up environment configuration...${NC}"
if [ ! -f .env ]; then
    sudo -u www-data cp deploy/production.env.example .env
    echo -e "${RED}IMPORTANT: Edit /opt/ll-html/.env with your actual configuration values!${NC}"
fi

# Create static files directory
echo -e "${YELLOW}Creating static files directory...${NC}"
sudo -u www-data mkdir -p staticfiles media

# Collect static files
echo -e "${YELLOW}Collecting static files...${NC}"
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
sudo -u www-data ./venv/bin/python manage.py migrate

# Create superuser (optional)
read -p "Do you want to create a Django superuser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo -u www-data ./venv/bin/python manage.py createsuperuser
fi

# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
sudo cp deploy/ll-html.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ll-html

# Configure nginx
echo -e "${YELLOW}Configuring nginx...${NC}"
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ll-html

# Add rate limiting to nginx.conf if not present
if ! grep -q "limit_req_zone" /etc/nginx/nginx.conf; then
    sudo sed -i '/http {/a\\tlimit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;' /etc/nginx/nginx.conf
fi

# Enable site
sudo ln -sf /etc/nginx/sites-available/ll-html /etc/nginx/sites-enabled/
sudo nginx -t

# Configure firewall
echo -e "${YELLOW}Configuring firewall...${NC}"
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# Start services
echo -e "${YELLOW}Starting services...${NC}"
sudo systemctl start ll-html
sudo systemctl reload nginx

# Setup SSL certificate with Let's Encrypt
echo -e "${YELLOW}Setting up SSL certificate with Let's Encrypt...${NC}"
echo -e "${RED}Make sure llhtml.whydidweevendothis.com points to this server before proceeding!${NC}"
read -p "Is your domain pointing to this server? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo certbot --nginx -d llhtml.whydidweevendothis.com --non-interactive --agree-tos --email admin@whydidweevendothis.com
    
    # Setup automatic renewal
    echo -e "${YELLOW}Setting up automatic certificate renewal...${NC}"
    sudo systemctl enable certbot.timer
    sudo systemctl start certbot.timer
else
    echo -e "${YELLOW}Skipping SSL setup. Run this manually later:${NC}"
    echo "sudo certbot --nginx -d llhtml.whydidweevendothis.com"
fi

# Final service restart
sudo systemctl restart ll-html nginx

# Check service status
echo -e "${YELLOW}Checking service status...${NC}"
sudo systemctl status ll-html --no-pager -l

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit /opt/ll-html/.env with your actual configuration"
echo "2. Point your domain (llhtml.whydidweevendothis.com) to this server's IP"
echo "3. If you skipped SSL setup, run: sudo certbot --nginx -d llhtml.whydidweevendothis.com"
echo "4. Restart services: sudo systemctl restart ll-html nginx"
echo ""
echo -e "${GREEN}Your application should be accessible at https://llhtml.whydidweevendothis.com${NC}"