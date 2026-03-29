# 🚀 YOUR DEPLOYMENT GUIDE - Render.com

**Configuration Complete!** ✅

Everything is configured for commercial deployment on Render.com (FREE forever).

---

## ✅ What's Configured

- ✅ Email: dhruv210803@gmail.com
- ✅ Platform: Render.com (Free)
- ✅ Commercial use: ENABLED
- ✅ AI denoise: DISABLED (commercial-safe)
- ✅ Secret key: Generated
- ✅ Privacy policy: Updated
- ✅ Terms of service: Updated

---

## 📋 Pre-Deployment Checklist

1. **Commit your code to GitHub:**
   ```bash
   cd /home/dhruv/Desktop/noise
   git init  # If not already a git repo
   git add .
   git commit -m "Production ready - commercial deployment"
   ```

2. **Push to GitHub:**
   - Create a new repository on GitHub
   - Follow GitHub's instructions to push your code

   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/noise-cleaner.git
   git branch -M main
   git push -u origin main
   ```

---

## 🚀 DEPLOY TO RENDER.COM (10 Minutes)

### Step 1: Create Render Account

1. Go to **[render.com](https://render.com)**
2. Click **"Get Started for Free"**
3. Sign up with **GitHub** (easiest)
4. **No credit card required!** ✅

### Step 2: Create Web Service

1. Click **"New +"** button (top right)
2. Select **"Web Service"**
3. Click **"Connect account"** to connect GitHub
4. Find and select your **noise-cleaner** repository
5. Click **"Connect"**

### Step 3: Configure Service

**Basic Settings:**
- **Name:** `noise-cleaner` (or whatever you like)
- **Region:** Choose closest to you (e.g., Oregon USA)
- **Branch:** `main`
- **Runtime:** `Python 3`

**Build Settings:**
- **Build Command:**
  ```bash
  pip install -e .
  ```

- **Start Command:**
  ```bash
  cd src && uvicorn noise_cleaner.app:app --host 0.0.0.0 --port $PORT
  ```

### Step 4: Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**

Add these **ONE BY ONE**:

```
ENABLE_AI_DENOISE=false
```
```
ENVIRONMENT=production
```
```
MAX_FILE_SIZE_MB=50
```
```
SECRET_KEY=a06d2f6adcccafdb6c82fc0cadc438164d28de55cedb07857de2ae1fc407a2d9
```
```
CORS_ORIGINS=https://noise-cleaner.onrender.com
```

*(Adjust CORS_ORIGINS if you chose a different name)*

### Step 5: Choose Plan

**IMPORTANT:** Select **"Free"** plan!
- Scroll down to Instance Type
- Select: **Free** (NOT Starter)
- Resources: 512 MB RAM, shared CPU

### Step 6: Deploy!

1. Click **"Create Web Service"**
2. Wait 5-10 minutes for first build
3. Watch the logs - you'll see:
   ```
   Build successful
   Starting service...
   Application startup complete
   ```

### Step 7: Get Your URL

Once deployed, you'll see:
```
Your service is live at https://noise-cleaner.onrender.com
```

**Visit it!** Your app is now live! 🎉

---

## ⚙️ Update CORS After First Deploy

After you know your exact Render URL:

1. Go to **Environment** tab in Render
2. Update `CORS_ORIGINS` to your actual URL
3. Click **"Save Changes"**
4. Service will auto-redeploy

---

## 🔍 Verify Deployment

Test these endpoints:

1. **Home page:**
   ```
   https://noise-cleaner.onrender.com
   ```

2. **Health check:**
   ```
   https://noise-cleaner.onrender.com/health
   ```

3. **Capabilities:**
   ```
   https://noise-cleaner.onrender.com/api/capabilities
   ```
   
   Should show: `"ai": false` (commercial-safe!)

---

## 📊 Important: Free Tier Behavior

**Sleep Mode:**
- After 15 minutes of inactivity, your app goes to sleep
- First request after sleep takes ~30 seconds to wake up
- Subsequent requests are instant
- **This is normal for free tier!**

**Keep it awake (optional):**
- Use UptimeRobot (free): pings every 5 minutes
- Go to [uptimerobot.com](https://uptimerobot.com)
- Add monitor: `https://noise-cleaner.onrender.com/health`
- Free tier: 50 monitors

---

## 💰 Add Revenue (Google AdSense)

Since AI is disabled, you can monetize!

1. **Apply for AdSense:**
   - Go to [google.com/adsense](https://google.com/adsense)
   - Sign up with your Google account
   - Add your site: `noise-cleaner.onrender.com`

2. **Verify ownership:**
   - Google gives you a verification code
   - Add to `src/noise_cleaner/static/index.html` in `<head>`

3. **Wait for approval:** 7-14 days

4. **Add ad units:**
   - Create ad units in AdSense dashboard
   - Add code to your pages
   - Commit and push to GitHub
   - Render auto-deploys

**Potential earnings:**
- 100 visitors/day × 2 pages × $0.50 CPM = ~$3/month
- 1,000 visitors/day = ~$30/month
- 10,000 visitors/day = ~$300/month

---

## 🎨 Custom Domain (Optional)

Want your own domain?

1. **Buy domain:** Namecheap, Porkbun ($1-12/year)

2. **Add to Render:**
   - Settings → Custom Domains → Add
   - Enter: `yourdomain.com`

3. **Update DNS:**
   - Add CNAME record: `yourdomain.com` → `noise-cleaner.onrender.com`

4. **SSL:** Automatic (free)

5. **Update .env:**
   ```bash
   CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

---

## 📈 Monitor Your App

**View Logs:**
- Render dashboard → Logs tab
- Real-time logging
- Filter by errors, warnings

**Metrics:**
- Render dashboard → Metrics tab
- CPU usage, memory, requests
- Free tier gets basic metrics

**External Monitoring:**
- [UptimeRobot](https://uptimerobot.com) - Free uptime monitoring
- [Plausible](https://plausible.io) - Privacy-friendly analytics

---

## 🔧 Update Your App

**Easy updates:**

1. Make changes locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update feature"
   git push
   ```
3. Render auto-deploys (2-3 minutes)
4. Done!

---

## 🆘 Troubleshooting

### Build fails
- Check logs in Render dashboard
- Ensure Python 3.10+ in requirements
- Verify all dependencies install

### 502 Bad Gateway
- Check if service is running (Render dashboard)
- View logs for errors
- Restart service: Settings → Manual Deploy → Deploy

### App slow to respond
- Normal for first request (waking from sleep)
- Use UptimeRobot to keep alive
- Or upgrade to paid tier ($7/month - always on)

### Can't upload files
- Check MAX_FILE_SIZE_MB in environment variables
- Free tier has limits - keep at 50MB

---

## 🎊 YOU'RE LIVE!

**Your app is deployed for FREE and ready for commercial use!**

**Next steps:**
1. Test all features
2. Share with friends
3. Apply for Google AdSense (if monetizing)
4. Set up monitoring (UptimeRobot)
5. Market your service!

**Your URLs:**
- **App:** https://noise-cleaner.onrender.com
- **Health:** https://noise-cleaner.onrender.com/health
- **Privacy:** https://noise-cleaner.onrender.com/privacy
- **Terms:** https://noise-cleaner.onrender.com/terms

---

## 📞 Need Help?

- **Render Docs:** [render.com/docs](https://render.com/docs)
- **Your Docs:** See DEPLOY-FREE.md, QUICK-REF.md
- **Email Support:** dhruv210803@gmail.com

---

**Congratulations! You're now running a professional audio processing service for FREE! 🎉🚀**
