# 🚀 Quick Reference Card

## Essential Commands

### Local Development
```bash
# Start development server
cd src && python -m noise_cleaner

# Or with uvicorn directly
uvicorn noise_cleaner.app:app --reload

# Access at: http://127.0.0.1:8000
```

### Production Deployment

```bash
# 1. Clone and setup
git clone <repo-url>
cd noise-cleaner
cp .env.example .env
nano .env  # Edit: ENABLE_AI_DENOISE=false, add SECRET_KEY

# 2. Build and start
docker compose up -d --build

# 3. Setup SSL
chmod +x setup-ssl.sh
./setup-ssl.sh

# 4. Check status
docker compose ps
docker compose logs -f

# 5. Visit
https://yourdomain.com
```

### Docker Commands

```bash
# View logs
docker compose logs -f
docker compose logs -f web    # Just web container
docker compose logs -f nginx  # Just nginx

# Restart services
docker compose restart
docker compose restart web

# Stop services
docker compose down

# Rebuild and restart
docker compose down
docker compose up -d --build

# Check resource usage
docker stats

# Clean up
docker system prune -a
```

### Monitoring

```bash
# Health check
curl https://yourdomain.com/health

# Test capabilities
curl https://yourdomain.com/api/capabilities

# Check disk space
df -h
du -sh temp/

# Check SSL expiry
sudo certbot certificates

# Renew SSL (automatic via cron)
sudo certbot renew --dry-run
```

### Troubleshooting

```bash
# Check if services are running
docker compose ps

# View recent errors
docker compose logs --tail=100 web

# Check nginx config
docker compose exec nginx nginx -t

# Restart if stuck
docker compose restart

# View environment variables
docker compose exec web env

# Access container shell
docker compose exec web bash
```

### Maintenance

```bash
# Update code
git pull
docker compose down
docker compose up -d --build

# Backup
tar -czf backup-$(date +%Y%m%d).tar.gz .env temp/

# Clean old files (runs automatically every hour)
# Manual: find temp/ -mtime +1 -delete

# Check temp file count
ls -1 temp/ | wc -l

# View system resource usage
htop
```

### File Locations

```
├── .env                    # Environment config (SECRET!)
├── docker-compose.yml      # Container orchestration
├── Dockerfile              # Container image
├── nginx.conf              # Reverse proxy config
├── setup-ssl.sh            # SSL setup script
├── temp/                   # Temporary files (auto-cleanup)
├── logs/                   # Application logs
└── src/noise_cleaner/
    ├── static/             # Frontend files
    ├── api/                # Backend routes
    └── config.py           # Configuration
```

### Environment Variables (Production)

```bash
# Critical settings
ENVIRONMENT=production
ENABLE_AI_DENOISE=false      # false for commercial!
SECRET_KEY=<generate-with-openssl-rand-hex-32>
CORS_ORIGINS=https://yourdomain.com

# Limits
MAX_FILE_SIZE_MB=100
RATE_LIMIT_PER_MINUTE=10

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=2
```

### SSL Certificate Renewal

```bash
# Auto-renewal via cron (configured by setup-ssl.sh)
# Runs daily at 3 AM

# Manual renewal
sudo certbot renew
docker compose restart nginx

# Force renewal
sudo certbot renew --force-renewal
```

### Security Checklist

```bash
# 1. Firewall (UFW)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 2. Fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# 3. SSH hardening
sudo nano /etc/ssh/sshd_config
# PermitRootLogin no
# PasswordAuthentication no

# 4. Automatic updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Performance Optimization

```bash
# Enable swap (for low-memory VPS)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Adjust swappiness
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Monitor disk I/O
iostat -x 1

# Monitor network
iftop
```

### Revenue Setup

**Google AdSense:**
```bash
# 1. Apply at google.com/adsense
# 2. Add verification code to index.html
# 3. Wait for approval (7-14 days)
# 4. Add ad units
# 5. Ensure ENABLE_AI_DENOISE=false
```

**Stripe (Freemium):**
```bash
# 1. Create account at stripe.com
# 2. Get API keys
# 3. Add to .env:
#    STRIPE_PUBLIC_KEY=pk_live_...
#    STRIPE_SECRET_KEY=sk_live_...
# 4. Implement user auth + payment flow
```

### Monitoring Setup

**UptimeRobot (Free):**
1. Go to uptimerobot.com
2. Add monitor: https://yourdomain.com/health
3. Set check interval: 5 minutes
4. Add email alert

**Google Analytics:**
```html
<!-- Add to static/index.html <head> -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Common Issues

**Port 8000 already in use:**
```bash
sudo lsof -i :8000
kill -9 <PID>
```

**Out of disk space:**
```bash
df -h
docker system prune -a
rm -rf temp/*
```

**High memory usage:**
```bash
# Reduce workers in .env
WORKERS=1
docker compose restart
```

**SSL certificate errors:**
```bash
# Check expiry
sudo certbot certificates

# Renew
sudo certbot renew
docker compose restart nginx
```

**502 Bad Gateway:**
```bash
# Check if backend is running
docker compose ps
docker compose logs web

# Restart
docker compose restart
```

### Cost Breakdown

| Item | Monthly | Annual |
|------|---------|--------|
| VPS (Hetzner CPX11) | €4.15 | €49.80 |
| Domain | ~$1 | $12 |
| SSL Certificate | $0 | $0 |
| **Total** | **~$6** | **~$67** |

### Revenue Potential

| Model | Users | Revenue/mo | Profit/mo |
|-------|-------|-----------|-----------|
| Ads | 1,000/day | $30 | $24 |
| Freemium | 10 Pro @ $5 | $50 | $44 |
| Pay-per-use | 100 files @ $0.10 | $10 | $4 |
| Combo | Mixed | $100+ | $94+ |

### Launch Checklist (Critical Only)

- [ ] `ENABLE_AI_DENOISE=false` (if commercial)
- [ ] `SECRET_KEY` generated and set
- [ ] `CORS_ORIGINS` configured
- [ ] Privacy policy updated with your details
- [ ] Terms of service updated with your details
- [ ] SSL certificate installed
- [ ] Health endpoint responding
- [ ] DNS A record configured
- [ ] Firewall configured (22, 80, 443 only)
- [ ] Tested on mobile device

**If all above ✅ → LAUNCH! 🚀**

---

## Support

- 📚 Full deployment guide: [DEPLOY.md](DEPLOY.md)
- 🔍 Production readiness: [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md)
- ✅ Complete checklist: [CHECKLIST.md](CHECKLIST.md)
- 📋 Summary: [SUMMARY.md](SUMMARY.md)

---

**Keep this file handy for quick reference during deployment and maintenance!**
