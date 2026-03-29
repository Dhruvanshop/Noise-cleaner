# ⚠️ CRITICAL: Read Before Going Live

## Legal / Licensing Blockers

### 🚨 DNS-64 (AI Denoiser) — CC-BY-NC 4.0 License

**The `denoiser` library (Facebook's DNS-64) uses Creative Commons Attribution-NonCommercial 4.0 International license.**

**This means:**
- ❌ **CANNOT** use it in any commercial service
- ❌ **CANNOT** show ads on pages that use it
- ❌ **CANNOT** charge for processing if using the AI model
- ❌ **CANNOT** generate revenue from it in any form

**Your options:**

### Option 1: Remove AI Denoise (Recommended for Revenue)
```python
# In denoise.py, force algorithm mode:
# Change line ~50 from:
use_ai = (backend == "ai") or (backend == "auto" and _AI_AVAILABLE)
# To:
use_ai = False  # Always use Wiener filter (no licensing restrictions)
```

Then remove the "AI" toggle from the UI.

**✅ Allows**: Full commercialization with ads, subscriptions, paid processing

---

### Option 2: Non-Commercial Only (No Revenue)
Keep DNS-64 but:
- **Remove all ads**
- **Remove all payment/subscription features**
- **Add clear notice**: "Non-commercial use only. No ads, no fees."
- Use donations only (still risky — consult lawyer)

---

### Option 3: Freemium Hybrid
- **Free tier**: Uses algorithm mode only (Wiener filter) — fully commercial-safe
- **Pro tier**: Adds AI denoising but requires account + manual approval for non-commercial use only
- Add legal checkbox: "I certify this is for personal/research use, not commercial"

**This is complex and legally risky. Not recommended.**

---

## Other Licensing (All Safe for Commercial Use)

| Library | License | Commercial OK? |
|---------|---------|----------------|
| FastAPI | MIT | ✅ Yes |
| Demucs (stem splitter) | MIT | ✅ Yes |
| Whisper (transcription) | MIT | ✅ Yes |
| scipy, numpy, soundfile | BSD | ✅ Yes |
| All our custom code | Your choice | ✅ Yes |

---

## Production Readiness Checklist

### Security
- [ ] Add file size limits (currently unlimited → DoS risk)
- [ ] Add rate limiting per IP
- [ ] Add CORS headers
- [ ] Add input validation
- [ ] Use HTTPS only (no HTTP)
- [ ] Add authentication for admin features
- [ ] Sanitize all user inputs

### Performance
- [ ] Use nginx reverse proxy
- [ ] Enable gzip compression
- [ ] Add CDN for static files
- [ ] Use uvicorn with multiple workers
- [ ] Add Redis for job queue (instead of in-memory registry)
- [ ] Move temp files to persistent storage (S3/DigitalOcean Spaces)

### Monitoring
- [ ] Add health check endpoint
- [ ] Add Sentry or similar error tracking
- [ ] Add uptime monitoring (UptimeRobot, Pingdom)
- [ ] Add analytics (Plausible, Google Analytics)
- [ ] Log all errors to file

### Business
- [ ] Choose revenue model (see below)
- [ ] Add privacy policy
- [ ] Add terms of service
- [ ] Add GDPR compliance notice (if targeting EU)
- [ ] Add cookie consent banner
- [ ] Set up payment processing (Stripe, Paddle)

---

## Revenue Generation Options

### ✅ Safe Models (No DNS-64 Conflict)

**1. Freemium with Limits**
- Free: 5 files/day, max 10 MB, algorithm mode only
- Pro ($5/month): Unlimited, 100 MB files, faster processing, batch operations
- **Implementation**: Add user accounts, track usage in database

**2. Ads on Free Version**
- Show Google AdSense on free tier
- Pro tier removes ads
- **Implementation**: Add `<script>` tags, hide with CSS for pro users

**3. API Access Tiers**
- Hobbyist: 100 API calls/month free
- Developer: $10/month for 10,000 calls
- Business: Custom pricing
- **Implementation**: Add API keys, rate limiting per key

**4. Pay-Per-Use**
- Credit system: $0.10 per file processed
- No subscription required
- **Implementation**: Stripe Checkout, credit balance system

**5. Donations / Tips**
- "Buy me a coffee" button
- Ko-fi integration
- **Implementation**: Just add button — no backend needed

---

## Minimal Cost Deployment (~$7/month)

### Recommended Stack
```
VPS: Hetzner CPX11 (2 vCPU, 2 GB RAM) — €4.15/month
Domain: Namecheap .com — $12/year = $1/month
SSL: Let's Encrypt — FREE
Total: ~$7/month
```

### Setup Steps
1. Rent VPS (Hetzner, DigitalOcean, Linode)
2. Install Docker + Docker Compose
3. Point domain A record to VPS IP
4. Deploy with provided docker-compose.yml
5. Run certbot for SSL
6. Configure nginx reverse proxy

---

## Recommended Actions (Priority Order)

### Immediate (Before Live)
1. **DECIDE**: Keep or remove AI denoising?
   - If keeping: Add non-commercial notice
   - If removing: Delete DNS-64 code, force algorithm mode
2. Add file size limit (recommend 100 MB max)
3. Add rate limiting (5 requests/minute per IP)
4. Write privacy policy + ToS
5. Test all endpoints on production server

### Week 1
1. Deploy to VPS with Docker
2. Set up SSL certificate
3. Add Google Analytics
4. Add basic error logging
5. Test with real users

### Month 1
1. Implement chosen revenue model
2. Add user accounts if needed
3. Set up payment processing
4. Add uptime monitoring
5. Optimize performance based on usage

---

## Security Warnings

⚠️ **Current vulnerabilities:**
- No authentication → anyone can use unlimited resources
- No file size limit → can fill disk with huge files
- No rate limiting → can DoS with many requests
- TEMP_DIR on disk → fills up over time if cleanup fails
- No CORS protection → can be embedded in malicious sites
- Running as root (if deployed incorrectly) → security risk

**These MUST be fixed before going live with real users.**
