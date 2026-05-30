#!/bin/bash
# Deploy Web2MD API to production
# Usage: ./deploy.sh [render|railway|vercel|all]
# Options:
#   render  - Deploy to Render (auto-detected from render.yaml)
#   railway - Deploy to Railway (requires Railway CLI + login)
#   vercel  - Deploy to Vercel (requires Vercel CLI + login)
#   ssh     - Deploy to your own VPS
#   all     - Deploy everywhere possible
#
# Requires: git push to trigger auto-deployment on Render/Railway

set -e

API_REPO="wang4866/api-marketplace"
API_URL="http://localhost:8000"

echo "=== Web2MD API Deployment Script ==="
echo ""

case "${1:-help}" in
  render)
    echo "1. Go to https://dashboard.render.com/static"
    echo "2. Click 'New +' → 'Web Service'"
    echo "3. Connect GitHub repo: $API_REPO"
    echo "4. Render will auto-detect render.yaml and deploy"
    echo ""
    echo "Or use Deploy Hook (if already set up):"
    if [ -n "$RENDER_DEPLOY_HOOK" ]; then
      curl -X POST "$RENDER_DEPLOY_HOOK"
      echo "Deploy triggered!"
    else
      echo "Set RENDER_DEPLOY_HOOK env var to trigger auto-deploy"
    fi
    ;;

  railway)
    echo "1. Go to https://railway.app/dashboard"
    echo "2. Click 'New Project' → 'Deploy from GitHub repo'"
    echo "3. Select: $API_REPO"
    echo "4. Railway auto-detects Python and runs the app"
    echo ""
    echo "To set start command manually in Railway:"
    echo "  Start Command: uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
    ;;

  vercel)
    echo "Vercel deployment for the static site only:"
    echo "  Project: $API_REPO/site/"
    echo "  To deploy: cd site && vercel --prod"
    ;;

  help|*)
    echo "Usage: ./deploy.sh [render|railway|vercel|ssh]"
    echo ""
    echo "Current API running at: $API_URL"
    echo "GitHub Pages site: https://wang4866.github.io/api-marketplace/"
    echo ""
    echo "Quick start:"
    echo "  ./deploy.sh render   # Deploy FastAPI to Render"
    echo "  ./deploy.sh vercel   # Deploy landing page to Vercel"
    echo ""
    echo "After deployment, update site/js/api-config.js with the public API URL."
    ;;
esac
