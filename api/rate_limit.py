"""
api/rate_limit.py — Rate Limiting Helpers
==========================================
Centralises SlowAPI configuration so limits are defined in one place
and referenced consistently across all route decorators.

Usage in main.py:
    from api.rate_limit import limiter, CHAT_LIMIT, KNOWLEDGE_LIMIT

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.post("/chat")
    @limiter.limit(CHAT_LIMIT)
    async def chat(request: Request, ...):
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# ── Limiter instance (shared across the app) ─────────────────────────────────

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/day", "50/hour"],
)

# ── Per-endpoint limits ───────────────────────────────────────────────────────

# Regular users: chat endpoint
CHAT_LIMIT = "20/minute"

# Admins: knowledge update (heavy I/O — restrict more aggressively)
KNOWLEDGE_UPDATE_LIMIT = "5/minute"

# Benchmark trigger: very expensive, only a few per hour
BENCHMARK_LIMIT = "3/hour"

# Auth token endpoint: prevent brute-force
AUTH_LIMIT = "10/minute"
