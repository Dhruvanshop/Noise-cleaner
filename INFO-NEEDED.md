# ℹ️ Information Needed From You

To complete the setup and deploy your Noise Cleaner application, I need the following information from you:

---

## 📧 1. Contact Information

### Your Email Address
**Used for:**
- Privacy Policy contact section
- Terms of Service contact
- SSL certificate registration (if self-hosting)
- DMCA/legal notices

**Example:** `hello@yourdomain.com` or `yourname@gmail.com`

**Provide here:** _________________________________

---

## 🌐 2. Domain Name (Optional)

### Do you have a domain?

**Option A: Yes, I have a domain**
- Domain name: _________________________________
- Example: `myapp.com`

**Option B: No domain yet**
- You'll use platform subdomain (free):
  - Railway: `yourapp.up.railway.app`
  - Render: `yourapp.onrender.com`
  - Fly.io: `yourapp.fly.dev`

**Option C: Will buy later**
- Cheap domains ($1-2/year):
  - Namecheap: .xyz, .online
  - Porkbun: Various TLDs
  - CloudFlare: At-cost pricing

---

## 🎵 3. AI Denoising Decision (CRITICAL!)

### Do you want to enable AI denoising?

**⚠️ IMPORTANT:** This affects what you can do with your service!

**Option A: NO - Disable AI (RECOMMENDED)**
- ✅ Can show ads (Google AdSense, etc.)
- ✅ Can charge for features
- ✅ Can offer paid subscriptions
- ✅ Fully commercial use
- ❌ No AI denoising (algorithm mode only)
- **Choose this if:** You want to make money

**Option B: YES - Enable AI**
- ✅ AI denoising with DNS-64 model
- ✅ Better noise reduction quality
- ❌ **NO ADS** - violates license
- ❌ **NO PAID FEATURES** - violates license
- ❌ **NO REVENUE** of any kind
- **Choose this if:** Personal/educational use only

**Your choice:** [ ] Disable AI (commercial) [ ] Enable AI (non-commercial)

---

## 🚀 4. Deployment Platform

### Where do you want to deploy?

**Easiest Options (FREE):**

### Railway.app
- **Cost:** $5/month credit (free trial)
- **Setup time:** 5 minutes
- **Difficulty:** ⭐ (easiest!)
- **Credit card:** Not required for trial
- **Always on:** No (sleeps after inactivity)
- **Best for:** Quick deployment, testing

[ ] Choose Railway

### Render.com
- **Cost:** $0 forever
- **Setup time:** 10 minutes
- **Difficulty:** ⭐⭐ (easy)
- **Credit card:** NOT required
- **Always on:** No (sleeps after 15 min)
- **Best for:** Free forever, no card needed

[ ] Choose Render

### Fly.io
- **Cost:** $0 (3 free VMs)
- **Setup time:** 15 minutes
- **Difficulty:** ⭐⭐⭐ (medium)
- **Credit card:** Required (won't charge on free tier)
- **Always on:** Auto start/stop
- **Best for:** Fast cold starts, global CDN

[ ] Choose Fly.io

### Oracle Cloud (Always Free)
- **Cost:** $0 FOREVER (never expires)
- **Setup time:** 30 minutes
- **Difficulty:** ⭐⭐⭐⭐ (advanced)
- **Credit card:** Required (verification only)
- **Always on:** YES (24/7)
- **Best for:** Production, always-on, generous resources

[ ] Choose Oracle Cloud

### Self-Hosted VPS
- **Cost:** ~$5-7/month
- **Setup time:** 1 hour
- **Difficulty:** ⭐⭐⭐⭐ (advanced)
- **Credit card:** Required
- **Always on:** YES
- **Best for:** Full control, custom setup

[ ] Choose VPS (Hetzner/DigitalOcean/Linode)

### Skip for now
[ ] I'll decide later

---

## 📋 5. Additional Information (Optional)

### Server Location Preference
Where are most of your users located?

- [ ] North America (US/Canada)
- [ ] Europe
- [ ] Asia
- [ ] Other: _________________________________

This helps choose the best datacenter region.

### Expected Traffic
How many users do you expect?

- [ ] Just me (testing)
- [ ] <100 users/day (hobby)
- [ ] 100-1,000 users/day (small)
- [ ] 1,000+ users/day (medium)

This helps size resources appropriately.

### Monetization Plans
How do you plan to make money? (if commercial)

- [ ] Google AdSense
- [ ] Freemium (free + paid tiers)
- [ ] Donations
- [ ] API access sales
- [ ] Not planning to monetize
- [ ] Haven't decided yet

---

## 📝 Summary Checklist

Before running `./setup.sh`, make sure you have:

- [ ] Email address decided
- [ ] Domain situation clarified (have one / use free / buy later)
- [ ] AI denoising decision made (commercial vs non-commercial)
- [ ] Deployment platform chosen
- [ ] Optional: Server location preference
- [ ] Optional: Traffic estimate
- [ ] Optional: Monetization plan

---

## 🎯 What Happens Next

### If you run `./setup.sh`:

1. **You'll be prompted for:**
   - Email address
   - Domain (can skip)
   - AI preference
   - Deployment platform

2. **Script will automatically:**
   - Generate secure secret key
   - Create `.env` file
   - Update privacy.html with your email
   - Update terms.html with your email
   - Show deployment instructions for your platform

3. **Then you:**
   - Follow platform-specific guide
   - Deploy in 5-30 minutes
   - App is live!

### If you provide information now:

I can configure everything for you immediately:

1. Update all configuration files
2. Set correct defaults
3. Prepare deployment files
4. Give you exact commands to run

---

## 📞 Ready to Proceed?

**Provide the information above, then I'll:**

1. ✅ Configure `.env` with your settings
2. ✅ Update privacy.html and terms.html with your email/domain
3. ✅ Set up deployment files for your chosen platform
4. ✅ Give you exact step-by-step deployment commands
5. ✅ Make everything production-ready

**OR just run:** `./setup.sh` and answer the prompts interactively!

---

## 🆘 Questions?

### "I don't have an email/domain yet"
No problem! Use placeholders:
- Email: `admin@example.com` (update later)
- Domain: Use platform subdomain (free)

### "I'm not sure about AI denoising"
**Safe choice:** Disable it (set to false)
- You can always enable it later
- Keeps your options open for monetization

### "Which platform should I choose?"
**Quick answer:**
- **No credit card:** Render.com
- **Easiest:** Railway.app
- **Production:** Oracle Cloud (free forever)
- **Testing:** Render or Railway

### "Can I change my mind later?"
**Yes!** Everything can be updated:
- Email/domain: Edit HTML files
- AI setting: Change .env variable
- Platform: Redeploy anywhere
- Monetization: Add anytime

---

**Ready? Provide your information above, or run `./setup.sh` now! 🚀**
