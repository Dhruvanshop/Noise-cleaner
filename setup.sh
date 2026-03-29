#!/bin/bash
# Interactive Setup Script for Noise Cleaner
# This script collects your information and configures the application

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║                                                   ║"
echo "║        🎵  Noise Cleaner Setup Wizard  🎵        ║"
echo "║                                                   ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check if .env already exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file already exists.${NC}"
    read -p "Overwrite? (y/n): " OVERWRITE
    if [ "$OVERWRITE" != "y" ]; then
        echo "Exiting. Your existing .env was not modified."
        exit 0
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Contact Information
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${GREEN}Step 1: Contact Information${NC}"
echo "This will be used in your Privacy Policy and Terms of Service."
echo ""

read -p "Your email address (e.g., hello@example.com): " USER_EMAIL
while [ -z "$USER_EMAIL" ]; do
    echo -e "${RED}Email cannot be empty!${NC}"
    read -p "Your email address: " USER_EMAIL
done

read -p "Your domain name (or press Enter to use platform subdomain): " USER_DOMAIN
if [ -z "$USER_DOMAIN" ]; then
    USER_DOMAIN="yourapp.onrender.com"
    echo -e "${YELLOW}No domain provided. Using placeholder: $USER_DOMAIN${NC}"
    echo "You can update this later in privacy.html and terms.html"
fi

# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Licensing Decision
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${GREEN}Step 2: Licensing Decision${NC}"
echo ""
echo -e "${YELLOW}⚠️  CRITICAL LICENSE DECISION${NC}"
echo ""
echo "The AI denoising feature uses Facebook's DNS-64 model which has a"
echo "CC-BY-NC (Non-Commercial) license. This means:"
echo ""
echo -e "${RED}  ✗ NO ads or monetization if AI enabled${NC}"
echo -e "${RED}  ✗ NO paid features or subscriptions${NC}"
echo -e "${RED}  ✗ NO commercial use of any kind${NC}"
echo ""
echo "If you disable AI denoising, you can:"
echo -e "${GREEN}  ✓ Show ads (Google AdSense, etc.)${NC}"
echo -e "${GREEN}  ✓ Charge for premium features${NC}"
echo -e "${GREEN}  ✓ Use commercially without restrictions${NC}"
echo ""
echo "All other features (stems, normalize, convert, etc.) are fully commercial-safe."
echo ""
echo "Options:"
echo "  1) Disable AI - Commercial use allowed (RECOMMENDED)"
echo "  2) Enable AI - Non-commercial only"
echo "  3) I'll decide later (defaults to disabled for safety)"
echo ""
read -p "Your choice (1/2/3): " AI_CHOICE

case $AI_CHOICE in
    2)
        ENABLE_AI="true"
        echo -e "${YELLOW}⚠️  AI enabled - YOU CANNOT MONETIZE THIS SERVICE!${NC}"
        ;;
    *)
        ENABLE_AI="false"
        echo -e "${GREEN}✓ AI disabled - Commercial use allowed${NC}"
        ;;
esac

# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Deployment Platform
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${GREEN}Step 3: Deployment Platform${NC}"
echo ""
echo "Where do you want to deploy?"
echo ""
echo "  1) Railway.app - Easiest, $5/month credit (RECOMMENDED)"
echo "  2) Render.com - Free forever, sleeps after 15min"
echo "  3) Fly.io - Fast, 3 free VMs"
echo "  4) Oracle Cloud - Most powerful, always on, FREE FOREVER"
echo "  5) Self-hosted VPS (Hetzner, DigitalOcean, etc.)"
echo "  6) Skip for now"
echo ""
read -p "Your choice (1-6): " DEPLOY_CHOICE

case $DEPLOY_CHOICE in
    1) PLATFORM="Railway" ;;
    2) PLATFORM="Render" ;;
    3) PLATFORM="Fly.io" ;;
    4) PLATFORM="Oracle Cloud" ;;
    5) PLATFORM="VPS" ;;
    *) PLATFORM="none" ;;
esac

# ═══════════════════════════════════════════════════════════════════════════
# Step 4: Generate Secret Key
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${GREEN}Step 4: Security${NC}"
echo "Generating secure secret key..."

if command -v openssl &> /dev/null; then
    SECRET_KEY=$(openssl rand -hex 32)
    echo -e "${GREEN}✓ Secret key generated${NC}"
else
    SECRET_KEY="CHANGE_ME_$(date +%s)_$(shuf -i 1000-9999 -n 1)"
    echo -e "${YELLOW}⚠️  OpenSSL not found. Using fallback key.${NC}"
    echo "   Consider generating a proper key with: openssl rand -hex 32"
fi

# ═══════════════════════════════════════════════════════════════════════════
# Step 5: Create .env file
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${GREEN}Step 5: Creating configuration${NC}"

cat > .env << EOF
# ══════════════════════════════════════════════════════════════════════════════
# Noise Cleaner Configuration
# Generated: $(date)
# ══════════════════════════════════════════════════════════════════════════════

# ── Environment ───────────────────────────────────────────────────────────────
ENVIRONMENT=production
DEBUG=false

# ── Server ────────────────────────────────────────────────────────────────────
HOST=0.0.0.0
PORT=8000
WORKERS=1

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY=$SECRET_KEY
CORS_ORIGINS=https://$USER_DOMAIN,https://www.$USER_DOMAIN

# ── Features ──────────────────────────────────────────────────────────────────
# ⚠️  CRITICAL: DNS-64 AI is CC-BY-NC licensed (Non-Commercial)
# Keep this FALSE if you plan to monetize (ads, subscriptions, etc.)
ENABLE_AI_DENOISE=$ENABLE_AI

# ── File Limits ───────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB=50
RATE_LIMIT_PER_MINUTE=10

# ── Storage ───────────────────────────────────────────────────────────────────
TEMP_DIR=/tmp/noise_cleaner
JOB_TTL_SECONDS=3600

# ── Contact Information ───────────────────────────────────────────────────────
CONTACT_EMAIL=$USER_EMAIL
DOMAIN=$USER_DOMAIN

# ── Deployment Platform ───────────────────────────────────────────────────────
# Platform: $PLATFORM
EOF

echo -e "${GREEN}✓ .env file created${NC}"

# ═══════════════════════════════════════════════════════════════════════════
# Step 6: Update Privacy Policy and Terms
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${GREEN}Step 6: Updating legal documents${NC}"

# Update privacy.html
if [ -f "src/noise_cleaner/static/privacy.html" ]; then
    CURRENT_DATE=$(date "+%B %d, %Y")
    
    sed -i "s|\[TODO: ADD DATE[^]]*\]|$CURRENT_DATE|g" src/noise_cleaner/static/privacy.html
    sed -i "s|\[TODO: YOUR EMAIL[^]]*\]|$USER_EMAIL|g" src/noise_cleaner/static/privacy.html
    sed -i "s|\[TODO: YOUR DOMAIN[^]]*\]|https://$USER_DOMAIN|g" src/noise_cleaner/static/privacy.html
    sed -i "s|\[TODO: SPECIFY LOCATION[^]]*\]|$PLATFORM|g" src/noise_cleaner/static/privacy.html
    
    echo -e "${GREEN}✓ privacy.html updated${NC}"
else
    echo -e "${YELLOW}⚠️  privacy.html not found, skipping${NC}"
fi

# Update terms.html
if [ -f "src/noise_cleaner/static/terms.html" ]; then
    sed -i "s|\[TODO: ADD DATE[^]]*\]|$CURRENT_DATE|g" src/noise_cleaner/static/terms.html
    sed -i "s|\[TODO: YOUR EMAIL[^]]*\]|$USER_EMAIL|g" src/noise_cleaner/static/terms.html
    sed -i "s|\[TODO: YOUR DOMAIN[^]]*\]|https://$USER_DOMAIN|g" src/noise_cleaner/static/terms.html
    sed -i "s|\[TODO: YOUR JURISDICTION[^]]*\]|Laws of your jurisdiction|g" src/noise_cleaner/static/terms.html
    
    echo -e "${GREEN}✓ terms.html updated${NC}"
else
    echo -e "${YELLOW}⚠️  terms.html not found, skipping${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════
# Step 7: Summary & Next Steps
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║                                                   ║"
echo "║            ✓  Setup Complete!  ✓                 ║"
echo "║                                                   ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}Configuration Summary:${NC}"
echo "  • Email: $USER_EMAIL"
echo "  • Domain: $USER_DOMAIN"
echo "  • AI Denoising: $ENABLE_AI"
echo "  • Platform: $PLATFORM"
echo "  • Secret Key: Generated"
echo ""

if [ "$ENABLE_AI" = "true" ]; then
    echo -e "${YELLOW}⚠️  REMEMBER: AI enabled = NO COMMERCIAL USE!${NC}"
    echo ""
fi

echo -e "${GREEN}Next Steps:${NC}"
echo ""

case $DEPLOY_CHOICE in
    1)
        echo "  Railway Deployment:"
        echo "  1. Go to https://railway.app"
        echo "  2. Sign up with GitHub"
        echo "  3. New Project → Deploy from GitHub"
        echo "  4. Select your repository"
        echo "  5. Copy environment variables from .env to Railway"
        echo "  6. Deploy!"
        echo ""
        echo "  Your app will be live at: https://yourapp.up.railway.app"
        ;;
    2)
        echo "  Render.com Deployment:"
        echo "  1. Go to https://render.com"
        echo "  2. Sign up (no credit card needed)"
        echo "  3. New Web Service → Connect GitHub"
        echo "  4. Select your repository"
        echo "  5. Build: pip install -e ."
        echo "  6. Start: cd src && uvicorn noise_cleaner.app:app --host 0.0.0.0 --port \$PORT"
        echo "  7. Copy environment variables from .env"
        echo "  8. Choose FREE tier"
        echo "  9. Deploy!"
        echo ""
        echo "  Your app will be live at: https://yourapp.onrender.com"
        ;;
    3)
        echo "  Fly.io Deployment:"
        echo "  1. Install Fly CLI: curl -L https://fly.io/install.sh | sh"
        echo "  2. Sign up: fly auth signup"
        echo "  3. Deploy: fly launch (use defaults)"
        echo "  4. Your app is live!"
        echo ""
        echo "  Your app will be live at: https://yourapp.fly.dev"
        ;;
    4)
        echo "  Oracle Cloud Deployment:"
        echo "  1. Read DEPLOY-FREE.md - Oracle Cloud section"
        echo "  2. Create free account at oracle.com/cloud/free"
        echo "  3. Create ARM instance (always free)"
        echo "  4. Install Docker and deploy"
        echo ""
        ;;
    5)
        echo "  VPS Deployment:"
        echo "  1. Read DEPLOY.md for full instructions"
        echo "  2. Use docker-compose up -d --build"
        echo "  3. Run ./setup-ssl.sh for HTTPS"
        echo ""
        ;;
    *)
        echo "  1. Choose a deployment platform (see DEPLOY-FREE.md)"
        echo "  2. Follow the guide for your chosen platform"
        echo ""
        ;;
esac

echo -e "${BLUE}Documentation:${NC}"
echo "  • DEPLOY-FREE.md - Free deployment guides"
echo "  • DEPLOY.md - VPS deployment guide"
echo "  • PRODUCTION_READINESS.md - Complete production guide"
echo "  • QUICK-REF.md - Command reference"
echo ""

echo -e "${GREEN}Test locally:${NC}"
echo "  cd src && python -m noise_cleaner"
echo "  Then visit: http://localhost:8000"
echo ""

echo -e "${YELLOW}Don't forget to:${NC}"
echo "  • Review privacy.html and terms.html"
echo "  • Test your app locally before deploying"
echo "  • Set up monitoring (UptimeRobot is free)"
echo "  • Commit and push to GitHub"
echo ""

echo -e "${GREEN}Good luck! 🚀${NC}"
