# Deployment Guide

This guide will walk you through deploying Noise Cleaner to production with minimal cost (~$7/month).

## ⚠️ CRITICAL: Read PRODUCTION_READINESS.md First!

**Before deploying, you MUST read [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) and decide:**

- **Option A**: Set `ENABLE_AI_DENOISE=false` for commercial use (recommended)
- **Option B**: Set `ENABLE_AI_DENOISE=true` for non-commercial use only

**Do NOT deploy with AI denoise enabled if you plan to show ads, charge fees, or generate revenue in any way.**

---

## Prerequisites

- A domain name ($10-15/year from Namecheap, Porkbun, or CloudFlare)
- A VPS with at least 2GB RAM ($5-10/month from Hetzner, DigitalOcean, or Linode)
- Basic command line knowledge
- Git installed on your local machine

---

## Part 1: VPS Setup

### Option A: Hetzner (Recommended - €4.15/month)

1. Go to https://www.hetzner.com/cloud
2. Create an account
3. Create a new project
4. Add a server:
   - Location: Choose closest to your users
   - Image: **Ubuntu 22.04**
   - Type: **CPX11** (2 vCPU, 2GB RAM, 40GB SSD)
   - SSH Key: Add your public SSH key
   - Firewall: Create firewall allowing ports 22, 80, 443
   - Name: `noise-cleaner-prod`

5. Note the server IP address

### Option B: DigitalOcean ($6/month)

1. Go to https://www.digitalocean.com
2. Create a Droplet:
   - Image: Ubuntu 22.04 LTS
   - Plan: Basic ($6/month, 1 vCPU, 1GB RAM)
   - Add your SSH key
   - Enable monitoring (free)

### Option C: Linode ($5/month)

1. Go to https://www.linode.com
2. Create a Linode:
   - Image: Ubuntu 22.04 LTS
   - Plan: Nanode 1GB ($5/month)
   - Add SSH key

---

## Part 2: Domain Setup

1. **Buy a domain** from Namecheap, Porkbun, or CloudFlare
2. **Add A record** pointing to your VPS IP:
   ```
   Type: A
   Name: @
   Value: <your-vps-ip>
   TTL: 300
   ```
3. **Add www subdomain** (optional):
   ```
   Type: A
   Name: www
   Value: <your-vps-ip>
   TTL: 300
   ```

Wait 5-10 minutes for DNS to propagate. Check with:
```bash
dig yourdomain.com
```

---

## Part 3: Server Initial Setup

SSH into your server:
```bash
ssh root@<your-vps-ip>
```

### 1. Update system
```bash
apt update && apt upgrade -y
```

### 2. Create non-root user
```bash
adduser noisecleaner
usermod -aG sudo noisecleaner
```

### 3. Copy SSH key to new user
```bash
rsync --archive --chown=noisecleaner:noisecleaner ~/.ssh /home/noisecleaner
```

### 4. Exit and reconnect as new user
```bash
exit
ssh noisecleaner@<your-vps-ip>
```

### 5. Install Docker
```bash
# Install dependencies
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Restart session for group to take effect
exit
```

Reconnect:
```bash
ssh noisecleaner@<your-vps-ip>
```

Verify Docker:
```bash
docker --version
docker compose version
```

---

## Part 4: Deploy Application

### 1. Clone repository
```bash
cd ~
git clone https://github.com/yourusername/noise-cleaner.git
cd noise-cleaner
```

*(If you don't have a GitHub repo yet, copy files manually using `scp`)*

### 2. Create environment file
```bash
cp .env.example .env
nano .env
```

**Edit the following values:**

```bash
# CRITICAL: Choose your licensing model
ENABLE_AI_DENOISE=false  # Set to false for commercial use!

# Environment
ENVIRONMENT=production
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=2

# Security
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Limits
MAX_FILE_SIZE_MB=100
RATE_LIMIT_PER_MINUTE=10

# Storage
TEMP_DIR=/app/temp
JOB_TTL_SECONDS=3600
```

Generate a secret key:
```bash
openssl rand -hex 32
```

### 3. Update nginx.conf with your domain
```bash
nano nginx.conf
```

Replace `yourdomain.com` with your actual domain in:
- `server_name` directive
- SSL certificate paths

### 4. Build and start (HTTP only, temporarily)
```bash
# First, comment out SSL lines in nginx.conf temporarily
nano nginx.conf
# Comment out lines 15-19 (SSL certificate paths)

# Start containers
docker compose up -d --build
```

Check logs:
```bash
docker compose logs -f
```

Visit `http://yourdomain.com` to verify it works.

---

## Part 5: SSL Certificate Setup

### 1. Install Certbot
```bash
sudo apt install -y certbot
```

### 2. Stop nginx temporarily
```bash
docker compose stop nginx
```

### 3. Obtain SSL certificate
```bash
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

Follow the prompts:
- Enter your email
- Agree to Terms of Service
- Choose whether to share email

Your certificates will be saved to:
- `/etc/letsencrypt/live/yourdomain.com/fullchain.pem`
- `/etc/letsencrypt/live/yourdomain.com/privkey.pem`

### 4. Update nginx.conf SSL paths
```bash
nano nginx.conf
```

Uncomment SSL lines and update paths:
```nginx
ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
```

### 5. Update docker-compose.yml to mount SSL certs
```bash
nano docker-compose.yml
```

Add volume mount under nginx service:
```yaml
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./src/noise_cleaner/static:/usr/share/nginx/html/static:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro  # Add this line
```

### 6. Restart services
```bash
docker compose up -d
```

### 7. Test HTTPS
Visit `https://yourdomain.com` — you should see a secure lock icon.

### 8. Setup auto-renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Add cron job for auto-renewal
sudo crontab -e
```

Add this line:
```
0 3 * * * certbot renew --quiet --post-hook "cd /home/noisecleaner/noise-cleaner && docker compose restart nginx"
```

---

## Part 6: Monitoring & Maintenance

### Check service status
```bash
docker compose ps
docker compose logs -f web
docker compose logs -f nginx
```

### View resource usage
```bash
docker stats
```

### Restart services
```bash
docker compose restart
```

### Update application
```bash
git pull
docker compose down
docker compose up -d --build
```

### Backup data
```bash
# Backup temp files (if needed)
tar -czf backup-$(date +%Y%m%d).tar.gz temp/

# Copy to local machine
scp noisecleaner@<your-vps-ip>:~/backup-*.tar.gz ./
```

### Check disk space
```bash
df -h
docker system df
```

### Clean up old Docker images
```bash
docker system prune -a
```

---

## Part 7: Performance Optimization

### Enable swap (for 1-2GB VPS)
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Adjust swappiness
```bash
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

---

## Part 8: Revenue Generation Setup

### Option A: Google AdSense

1. Apply at https://www.google.com/adsense
2. Add verification code to `static/index.html`
3. Wait for approval (7-14 days)
4. Add ad units to your pages
5. **Ensure `ENABLE_AI_DENOISE=false`** (AI license prohibits commercial use)

### Option B: Freemium Model

1. Set up user authentication (see PRODUCTION_READINESS.md)
2. Implement usage tracking
3. Add Stripe payment integration
4. Create pricing tiers:
   - Free: 10 files/day, max 10MB
   - Pro ($5/month): 1000 files/day, max 100MB
   - Business ($20/month): Unlimited

### Option C: Donations

1. Add Ko-fi or Buy Me a Coffee button
2. Add PayPal donation button
3. Add GitHub Sponsors (if open source)
4. **If using donations with AI enabled, consult a lawyer** (CC-BY-NC may allow donations)

---

## Security Checklist

- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] SSH key authentication (no password login)
- [ ] Non-root user created
- [ ] SSL/HTTPS enabled
- [ ] Rate limiting configured
- [ ] File size limits enforced
- [ ] Regular updates scheduled
- [ ] Backups automated
- [ ] Monitoring enabled
- [ ] Error tracking setup (Sentry)
- [ ] CORS properly configured
- [ ] Secret key generated (not default)
- [ ] AI denoise disabled if commercial
- [ ] Privacy policy published
- [ ] Terms of service published

---

## Troubleshooting

### Port 80/443 blocked
```bash
# Check UFW firewall
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443

# Check if nginx is listening
sudo netstat -tlnp | grep :80
```

### Docker permission denied
```bash
# Make sure user is in docker group
groups
sudo usermod -aG docker $USER
# Log out and back in
```

### SSL certificate not renewing
```bash
# Check renewal
sudo certbot renew --dry-run

# View cron logs
grep CRON /var/log/syslog
```

### High memory usage
```bash
# Check container stats
docker stats

# Reduce workers in .env
WORKERS=1

# Restart
docker compose restart
```

### Files not uploading
```bash
# Check nginx body size
grep client_max_body_size nginx.conf

# Check app file size limit
grep MAX_FILE_SIZE_MB .env
```

---

## Cost Breakdown

| Item | Cost | Provider |
|------|------|----------|
| VPS (2GB RAM) | €4.15/mo | Hetzner CPX11 |
| Domain | $12/year | Namecheap |
| SSL Certificate | FREE | Let's Encrypt |
| **Total** | **~$7/month** | |

**Annual cost: ~$84**

---

## Next Steps

1. ✅ Deploy to production
2. ⏱ Monitor for 1 week
3. 📊 Add Google Analytics
4. 💰 Add revenue generation (ads/freemium)
5. 📧 Set up email notifications
6. 🔒 Add user accounts (if freemium)
7. 🎨 Customize branding
8. 📱 Make mobile-friendly
9. 🚀 Market your service

---

## Support

For issues:
1. Check logs: `docker compose logs -f`
2. Check GitHub Issues
3. Read PRODUCTION_READINESS.md
4. Search Stack Overflow

---

**Good luck! 🚀**
