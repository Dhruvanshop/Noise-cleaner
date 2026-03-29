#!/bin/bash
# Quick deployment script for Render.com
# Run this to prepare for deployment

set -e

echo "🚀 Preparing for Render.com deployment..."
echo ""

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    echo "✅ Git initialized"
else
    echo "✅ Git already initialized"
fi

# Create .gitignore if doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/
*.egg-info/
dist/
build/

# Environment
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temp files
temp/
*.log

# Don't ignore .env for deployment reference
# (but never commit secrets!)
EOF
    echo "✅ .gitignore created"
fi

# Add all files
echo ""
echo "📦 Adding files to git..."
git add .

# Show status
echo ""
echo "📊 Git status:"
git status --short

echo ""
echo "✅ Ready to commit!"
echo ""
echo "Next steps:"
echo "1. Commit: git commit -m 'Production ready - commercial deployment'"
echo "2. Create GitHub repo at: https://github.com/new"
echo "3. Push: git remote add origin YOUR_REPO_URL"
echo "4.       git branch -M main"
echo "5.       git push -u origin main"
echo "6. Follow DEPLOY-NOW.md for Render.com setup"
echo ""
echo "🚀 After pushing to GitHub, you can deploy to Render!"
