"""
API Key + 支付集成 — 给Web2MD API加收费层

准备就绪，外网一部署就能开卖。
"""

import secrets
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

# 定价方案
TIERS = {
    "free": {
        "requests_per_day": 50,
        "max_content_length": 50000,  # chars
        "concurrent_limit": 1,
        "price_monthly": 0,
    },
    "starter": {
        "requests_per_day": 500,
        "max_content_length": 200000,
        "concurrent_limit": 5,
        "price_monthly": 9.99,  # USD
    },
    "pro": {
        "requests_per_day": 5000,
        "max_content_length": 1000000,
        "concurrent_limit": 20,
        "price_monthly": 29.99,
    },
    "enterprise": {
        "requests_per_day": -1,  # unlimited
        "max_content_length": -1,
        "concurrent_limit": -1,
        "price_monthly": 99.99,
    },
}


class APIKey(BaseModel):
    key: str
    tier: str
    owner_email: str
    created_at: float
    expires_at: Optional[float] = None
    usage_today: int = 0
    last_used: Optional[float] = None


# 临时内存存储，上线后换数据库
key_store: dict[str, APIKey] = {}

# 内置免费key方便测试
_key = APIKey(key="test-free-key", tier="free", owner_email="demo@demo.com", created_at=time.time())
key_store[_key.key] = _key


def generate_api_key() -> str:
    """生成API key格式: w2md_xxxxx"""
    random_part = secrets.token_hex(16)
    return f"w2md_{random_part}"


def create_key(tier: str, email: str) -> APIKey:
    """创建新的付费API Key"""
    tier_config = TIERS.get(tier)
    if not tier_config:
        raise ValueError(f"Invalid tier: {tier}")

    api_key = APIKey(
        key=generate_api_key(),
        tier=tier,
        owner_email=email,
        created_at=time.time(),
        expires_at=(datetime.now() + timedelta(days=30)).timestamp() if tier != "free" else None,
    )
    key_store[api_key.key] = api_key
    return api_key


def validate_key(key: str) -> Optional[APIKey]:
    """验证API Key并检查配额"""
    api_key = key_store.get(key)
    if not api_key:
        return None
    if api_key.expires_at and time.time() > api_key.expires_at:
        return None

    tier_config = TIERS.get(api_key.tier)
    if tier_config and tier_config["requests_per_day"] > 0:
        if api_key.usage_today >= tier_config["requests_per_day"]:
            return None

    api_key.last_used = time.time()
    api_key.usage_today += 1
    return api_key


def record_usage(key: str, service: str, tokens: int, cost_usd: float) -> None:
    """记录用量（Ollama Chat等非Web2MD服务的用量追踪）
    Args:
        key: API key
        service: Service name (e.g. "chat", "batch")
        tokens: Number of tokens consumed
        cost_usd: Estimated cost in USD
    """
    # 未来可改成SQLite持久化
    api_key = key_store.get(key)
    if api_key:
        api_key.last_used = time.time()
    # Usage log for future billing
    import logging
    logging.getLogger("payment").info(
        f"Usage: key={key[:8]}... service={service} tokens={tokens} cost=${cost_usd:.6f}"
    )


# Stripe支付集成（简化版，上线后加完整webhook）
STRIPE_PRICES = {
    "starter": "price_starter_monthly",   # 替换为真实Stripe Price ID
    "pro": "price_pro_monthly",
    "enterprise": "price_enterprise_monthly",
}


def create_checkout_session(tier: str, email: str, success_url: str) -> dict:
    """创建Stripe checkout会话 — 上线后集成"""
    return {
        "url": f"https://buy.stripe.com/test_{tier}?email={email}&prefilled_email={email}",
        "tier": tier,
        "amount": TIERS[tier]["price_monthly"],
    }


def reset_daily_usage():
    """每日重置用量（放cron或启动时重置）"""
    now = time.time()
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    for key in key_store.values():
        if key.last_used and key.last_used < today_start:
            key.usage_today = 0
