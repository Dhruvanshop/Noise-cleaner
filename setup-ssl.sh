#!/bin/bash
# SSL Certificate Setup Script for Noise Cleaner
# Run this after deploying to VPS but before enabling HTTPS

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Noise Cleaner SSL Setup ===${NC}\n"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}ERROR: Do not run as root. Run as your normal user with sudo access.${NC}"
    exit 1
fi

# Prompt for domain
read -p "Enter your domain name (e.g., example.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo -e "${RED}ERROR: Domain cannot be empty${NC}"
    exit 1
fi

read -p "Enter your email for SSL certificate notifications: " EMAIL
if [ -z "$EMAIL" ]; then
    echo -e "${RED}ERROR: Email cannot be empty${NC}"
    exit 1
fi

read -p "Include www subdomain? (y/n): " INCLUDE_WWW

echo -e "\n${YELLOW}Step 1: Installing Certbot${NC}"
sudo apt update
sudo apt install -y certbot

echo -e "\n${YELLOW}Step 2: Stopping nginx container${NC}"
docker compose stop nginx

echo -e "\n${YELLOW}Step 3: Obtaining SSL certificate${NC}"
if [ "$INCLUDE_WWW" = "y" ]; then
    sudo certbot certonly --standalone -d "$DOMAIN" -d "www.$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive
else
    sudo certbot certonly --standalone -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive
fi

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ SSL certificate obtained successfully!${NC}"
    echo -e "Certificate location: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo -e "Private key location: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
else
    echo -e "\n${RED}✗ Failed to obtain SSL certificate${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 4: Updating nginx.conf${NC}"
# Backup original
cp nginx.conf nginx.conf.backup

# Update domain in nginx.conf
sed -i "s/yourdomain.com/$DOMAIN/g" nginx.conf

# Uncomment SSL certificate lines if they exist
sed -i 's/# ssl_certificate/ssl_certificate/g' nginx.conf

echo -e "${GREEN}✓ nginx.conf updated${NC}"

echo -e "\n${YELLOW}Step 5: Updating docker-compose.yml${NC}"
# Check if SSL volume mount already exists
if ! grep -q "/etc/letsencrypt:/etc/letsencrypt:ro" docker-compose.yml; then
    # Backup
    cp docker-compose.yml docker-compose.yml.backup
    
    # Add SSL volume mount under nginx service
    # This is a simple approach - in production you might want a more robust solution
    echo -e "${YELLOW}Note: You may need to manually add this line to docker-compose.yml under nginx volumes:${NC}"
    echo "      - /etc/letsencrypt:/etc/letsencrypt:ro"
fi

echo -e "\n${YELLOW}Step 6: Setting up auto-renewal${NC}"
# Add renewal cron job
CRON_CMD="0 3 * * * certbot renew --quiet --post-hook \"cd $(pwd) && docker compose restart nginx\""
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_CMD") | crontab -

echo -e "${GREEN}✓ Auto-renewal cron job added (runs daily at 3 AM)${NC}"

echo -e "\n${YELLOW}Step 7: Testing renewal${NC}"
sudo certbot renew --dry-run

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Renewal test successful${NC}"
else
    echo -e "${YELLOW}⚠ Renewal test failed, but certificates are installed${NC}"
fi

echo -e "\n${YELLOW}Step 8: Restarting services${NC}"
docker compose up -d

echo -e "\n${GREEN}=== SSL Setup Complete! ===${NC}\n"
echo -e "Your site should now be available at:"
echo -e "  ${GREEN}https://$DOMAIN${NC}"
if [ "$INCLUDE_WWW" = "y" ]; then
    echo -e "  ${GREEN}https://www.$DOMAIN${NC}"
fi
echo -e "\nCertificate will auto-renew every 60 days."
echo -e "\nBackup files created:"
echo -e "  - nginx.conf.backup"
echo -e "  - docker-compose.yml.backup (if modified)"
echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "  1. Test HTTPS: curl -I https://$DOMAIN"
echo -e "  2. Check SSL rating: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo -e "  3. Monitor logs: docker compose logs -f"
