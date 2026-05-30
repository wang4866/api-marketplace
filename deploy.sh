#!/bin/bash
# ============================================================
# api-marketplace — 一键部署脚本
# 用法: bash deploy.sh [platform]
#   platform: railway | vercel | render (默认: railway)
# ============================================================
set -e

PLATFORM="${1:-railway}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== API Marketplace 一键部署 ==="
echo "平台: $PLATFORM"
echo "目录: $ROOT"

# 检查依赖
command -v git >/dev/null 2>&1 || { echo "❌ 需要 git"; exit 1; }

case "$PLATFORM" in
  railway)
    command -v railway >/dev/null 2>&1 || { echo "⚠️  未安装 railway CLI: npm i -g @railway/cli"; }
    echo ""
    echo "--- Push to GitHub ---"
    git add -A
    git commit --allow-empty -m "deploy: $(date +%Y-%m-%d_%H:%M)"
    git push origin main
    echo ""
    echo "--- Deploy to Railway ---"
    echo "方法1: railway up"
    echo "方法2: 打开 https://railway.app/project/6cdc7b6a-c2d2-403c-ae66-d4dffe9d5936"
    echo ""
    echo "⚡ 部署后设置环境变量:"
    echo "  PORT=8000"
    echo "  OLLAMA_BASE=http://你的ollama地址:11434  (如有)
    echo ""
    ;;

  vercel)
    command -v vercel >/dev/null 2>&1 || { echo "⚠️  未安装 vercel CLI: npm i -g vercel"; }
    echo ""
    echo "--- Deploy to Vercel ---"
    echo "注意: Vercel 对 FastAPI 支持需 serverless 适配"
    echo "推荐: vercel --prod"
    echo ""
    echo "⚡ 或者直接从 GitHub 导入:"
    echo "  https://vercel.com/import"
    echo ""
    ;;

  render)
    echo ""
    echo "--- Deploy to Render ---"
    echo "打开 https://dashboard.render.com/blueprint"
    echo "导入: https://github.com/wang4866/api-marketplace"
    echo "配置文件已在 render.yaml (如需)"
    echo ""
    ;;

  *)
    echo "❌ 未知平台: $PLATFORM"
    echo "可选: railway | vercel | render"
    exit 1
    ;;
esac

echo ""
echo "=== 部署后验证 ==="
echo "curl https://你的域名/health"
echo "curl https://你的域名/pricing"
echo ""
echo "=== Stripe 支付接入 ==="
echo "1. 登录 https://dashboard.stripe.com"
echo "2. 创建产品: Starter(\$9.99/月), Pro(\$29.99/月), Enterprise(\$99.99/月)"
echo "3. 将 Price ID 写入 app/payment.py 的 STRIPE_PRICES"
echo "4. 在 Stripe 设置 webhook → 你的域名/stripe/webhook"
echo ""
echo "=== RapidAPI 上架 ==="
echo "1. 打开 https://rapidapi.com/hub"
echo "2. 创建 Provider → API Marketplace"
echo "3. 填入端点和定价"
echo ""
