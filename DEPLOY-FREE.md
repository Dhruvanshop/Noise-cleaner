# 🆓 Free Deployment Guide

Deploy Noise Cleaner **100% FREE** using these platforms. No credit card required for most!

---

## 🏆 Recommended: Railway.app (Easiest!)

**Free tier:** $5/month credit (enough for small projects)  
**Pros:** Automatic HTTPS, easy setup, GitHub integration  
**Cons:** Credit expires if unused, sleeps after inactivity

### Step-by-Step

1. **Sign up at [Railway.app](https://railway.app)**
   - Use GitHub login (no credit card needed for trial)

2. **Create new project → Deploy from GitHub**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize Railway to access your repos
   - Select your noise-cleaner repository

3. **Configure environment variables**
   - In Railway dashboard, go to Variables tab
   - Add these:
   ```bash
   ENABLE_AI_DENOISE=false
   ENVIRONMENT=production
   MAX_FILE_SIZE_MB=50
   PORT=8000
   ```

4. **Create Procfile** (Railway needs this)
   ```bash
   web: cd src && uvicorn noise_cleaner.app:app --host 0.0.0.0 --port $PORT
   ```

5. **Deploy!**
   - Railway auto-deploys on git push
   - You'll get a URL like: `noise-cleaner-production.up.railway.app`
   - HTTPS is automatic!

6. **Add custom domain (optional)**
   - Settings → Domains → Add custom domain
   - Point your DNS to Railway
   - SSL is automatic

**Done! Your app is live for FREE! 🎉**

---

## 🥈 Option 2: Render.com (Most Generous Free Tier)

**Free tier:** Free forever, 750 hours/month  
**Pros:** No credit card required, auto-deploy from GitHub  
**Cons:** Spins down after 15 min inactivity (cold starts ~30s)

### Step-by-Step

1. **Sign up at [Render.com](https://render.com)**

2. **Create new Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select noise-cleaner repo

3. **Configure service**
   ```
   Name: noise-cleaner
   Environment: Python 3
   Build Command: pip install -e .
   Start Command: cd src && uvicorn noise_cleaner.app:app --host 0.0.0.0 --port $PORT
   ```

4. **Add environment variables**
   - Click "Environment" tab
   - Add:
   ```bash
   ENABLE_AI_DENOISE=false
   ENVIRONMENT=production
   MAX_FILE_SIZE_MB=50
   PYTHON_VERSION=3.12
   ```

5. **Choose Free tier**
   - Instance Type: **Free**

6. **Deploy!**
   - Click "Create Web Service"
   - Wait ~5 minutes for first build
   - You'll get: `https://noise-cleaner.onrender.com`

7. **Custom domain (optional)**
   - Settings → Custom Domain → Add
   - Free SSL included

**Trade-off:** App sleeps after 15 min → First request takes ~30s to wake up. Subsequent requests are fast.

---

## 🥉 Option 3: Fly.io (Best Performance)

**Free tier:** 3 shared VMs, 160GB bandwidth  
**Pros:** Fast, near-instant cold starts, global CDN  
**Cons:** Requires credit card (but won't charge on free tier)

### Step-by-Step

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Sign up**
   ```bash
   fly auth signup
   # Or: fly auth login
   ```

3. **Create fly.toml** in your repo
   ```toml
   app = "noise-cleaner"
   
   [build]
     [build.args]
       PYTHON_VERSION = "3.12"
   
   [env]
     PORT = "8000"
     ENABLE_AI_DENOISE = "false"
     ENVIRONMENT = "production"
   
   [http_service]
     internal_port = 8000
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0
   
   [[vm]]
     cpu_kind = "shared"
     cpus = 1
     memory_mb = 256
   ```

4. **Create Dockerfile** (already exists in your repo!)

5. **Deploy**
   ```bash
   fly launch
   # Answer prompts (use defaults)
   
   fly deploy
   ```

6. **Your app is live!**
   ```
   https://noise-cleaner.fly.dev
   ```

7. **Custom domain**
   ```bash
   fly certs add yourdomain.com
   # Then point DNS to Fly
   ```

**Best for:** Apps that need fast response times even after inactivity.

---

## 🏅 Option 4: Oracle Cloud (Most Generous)

**Free tier:** Always free ARM instances, 200GB bandwidth  
**Pros:** Never expires, generous resources, full VM control  
**Cons:** More complex setup, requires credit card

### Resources You Get FREE Forever
- 4 ARM cores
- 24GB RAM (split across instances)
- 200GB storage
- 10TB/month bandwidth

### Quick Setup

1. **Sign up at [Oracle Cloud](https://www.oracle.com/cloud/free/)**
   - Requires credit card but won't charge

2. **Create VM instance**
   - Compute → Instances → Create Instance
   - Image: **Ubuntu 22.04**
   - Shape: **VM.Standard.A1.Flex** (ARM - ALWAYS FREE)
   - OCPUs: 2, RAM: 12GB
   - Add your SSH key

3. **Configure firewall**
   - VCN → Security Lists → Ingress Rules
   - Add: 0.0.0.0/0 → TCP 80, 443

4. **SSH into instance**
   ```bash
   ssh ubuntu@<instance-ip>
   ```

5. **Install Docker**
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker ubuntu
   ```

6. **Clone and deploy**
   ```bash
   git clone <your-repo>
   cd noise-cleaner
   cp .env.example .env
   # Edit .env
   docker-compose up -d --build
   ```

7. **Point domain to IP**
   - Get instance IP from Oracle console
   - Add A record in your DNS

8. **Setup SSL**
   ```bash
   ./setup-ssl.sh
   ```

**Best for:** Production use with consistent traffic. Never sleeps!

---

## 🎁 Option 5: Google Cloud Run (Pay-as-you-go)

**Free tier:** 2 million requests/month, 360K vCPU-seconds  
**Pros:** Scales to zero (pay nothing when unused), fast cold starts  
**Cons:** Complex setup, requires credit card

### Quick Deploy

1. **Install gcloud CLI**
   ```bash
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Build and push container**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT-ID/noise-cleaner
   ```

3. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy noise-cleaner \
     --image gcr.io/PROJECT-ID/noise-cleaner \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars ENABLE_AI_DENOISE=false,ENVIRONMENT=production
   ```

4. **Get URL**
   - You'll get: `https://noise-cleaner-xxx-uc.a.run.app`

**Best for:** Unpredictable traffic patterns. Scales automatically.

---

## 🆓 Free Domain Options

If you don't have a domain:

1. **Use free subdomain from platform**
   - Railway: `*.up.railway.app`
   - Render: `*.onrender.com`
   - Fly.io: `*.fly.dev`

2. **Free domain providers**
   - [Freenom](https://www.freenom.com) - Free .tk, .ml, .ga domains
   - [DuckDNS](https://www.duckdns.org) - Free subdomain with DDNS

3. **Cheap domains ($1-2/year)**
   - Namecheap - .xyz, .online for $1-2
   - Porkbun - Competitive pricing
   - CloudFlare - At-cost pricing

---

## 📊 Free Tier Comparison

| Platform | Cost | RAM | Always On? | Cold Start | Custom Domain | SSL |
|----------|------|-----|------------|------------|---------------|-----|
| **Railway** | $5 credit/mo | 512MB | No (sleeps) | ~5s | Yes | Free |
| **Render** | Free | 512MB | No (15min) | ~30s | Yes | Free |
| **Fly.io** | Free | 256MB | No (auto) | ~1s | Yes | Free |
| **Oracle** | Free forever | 12GB | **YES** | N/A | Yes | Manual |
| **Cloud Run** | 2M req/mo | 256MB-2GB | Scales to 0 | ~2s | Yes | Free |

**Recommendation:**
- **Hobbyist/testing:** Render (simplest, no card needed)
- **Small traffic:** Railway (easy, generous)
- **Production ready:** Oracle (always on, powerful)
- **High traffic:** Cloud Run (scales automatically)

---

## 💡 Tips for Free Deployment

1. **Reduce resource usage**
   ```bash
   # In .env
   WORKERS=1  # Instead of 2-4
   MAX_FILE_SIZE_MB=50  # Instead of 100
   ```

2. **Enable auto-sleep** (save credits)
   - Most platforms sleep after inactivity
   - First request wakes it up (~5-30s delay)
   - Fine for low-traffic sites

3. **Use CDN for static files**
   - CloudFlare (free)
   - Reduces bandwidth usage

4. **Monitor usage**
   - Set up alerts before hitting limits
   - Check platform dashboard weekly

5. **Keep it simple**
   - Don't add heavy dependencies
   - Optimize images
   - Minify CSS/JS

---

## 🚀 Recommended Setup (100% Free)

**For best results:**

1. **Deploy on:** Render.com (no credit card, generous)
2. **Domain:** Use `yourapp.onrender.com` OR buy cheap domain ($1-2/year)
3. **SSL:** Automatic (included)
4. **Monitoring:** UptimeRobot (free)
5. **Analytics:** Plausible or Umami (self-hosted, free)

**Total cost: $0-2/year** (if buying domain)

---

## 📋 Pre-Deployment Checklist

- [ ] Set `ENABLE_AI_DENOISE=false` (avoids licensing issues)
- [ ] Update privacy.html with your email
- [ ] Update terms.html with your email
- [ ] Test locally: `cd src && python -m noise_cleaner`
- [ ] Commit all changes to GitHub
- [ ] Choose deployment platform
- [ ] Follow deployment guide above
- [ ] Test deployed app
- [ ] Set up monitoring (UptimeRobot)

---

## 🆘 Troubleshooting

**Build fails:**
- Check Python version (needs 3.10+)
- Ensure dependencies install correctly
- Check build logs in platform dashboard

**App crashes:**
- Check application logs
- Reduce `WORKERS=1` if memory limited
- Increase `MAX_FILE_SIZE_MB` if needed

**Slow performance:**
- Use platform with higher RAM allocation
- Enable gzip compression (already in nginx.conf)
- Consider upgrading to paid tier

**SSL errors:**
- Verify DNS points to platform
- Wait 5-10 minutes for SSL provisioning
- Check platform SSL settings

---

**Choose your platform and deploy for FREE! 🎉**
