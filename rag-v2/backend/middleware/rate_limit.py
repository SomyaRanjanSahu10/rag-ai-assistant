"""
Rate Limiting Middleware
========================
Simple in-memory sliding window rate limiter.
For production, use Redis-backed rate limiting (e.g., slowapi + redis).
"""

import time
import logging
from collections import defaultdict, deque
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Per-IP limits: (max_requests, window_seconds)
RATE_LIMITS = {
    "/api/auth/login": (10, 60),       # 10 login attempts per minute
    "/api/auth/register": (5, 60),     # 5 registrations per minute
    "/api/chat": (60, 60),             # 60 chat requests per minute
    "/api/upload": (20, 60),           # 20 uploads per minute
    "default": (120, 60),              # 120 requests per minute (general)
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # IP → deque of timestamps
        self._buckets: dict[str, dict[str, deque]] = defaultdict(lambda: defaultdict(deque))

    def _get_limit(self, path: str) -> tuple[int, int]:
        for prefix, limit in RATE_LIMITS.items():
            if prefix != "default" and path.startswith(prefix):
                return limit
        return RATE_LIMITS["default"]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else "unknown"
        )

        path = request.url.path
        max_req, window = self._get_limit(path)
        now = time.time()
        bucket = self._buckets[ip][path]

        # Remove timestamps outside the current window
        while bucket and bucket[0] < now - window:
            bucket.popleft()

        if len(bucket) >= max_req:
            logger.warning("Rate limit exceeded: IP=%s PATH=%s", ip, path)
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": {"code": "RATE_LIMIT", "message": "Too many requests. Please slow down."}},
                headers={"Retry-After": str(window)},
            )

        bucket.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(max_req - len(bucket))
        return response
