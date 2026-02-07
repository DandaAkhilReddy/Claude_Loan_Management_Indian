"""Middleware — rate limiting, request logging, error handling."""

import time
import logging
from collections import defaultdict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests with timing."""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.0f}ms)")
        response.headers["X-Response-Time"] = f"{elapsed:.0f}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter for OCR endpoints.

    NOTE: This is per-process. In a multi-worker deployment, replace with
    Redis-backed rate limiting (e.g. slowapi with Redis storage).
    """

    _MAX_TRACKED_IPS = 10_000
    _PRUNE_INTERVAL = 300  # seconds

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self._last_prune = time.time()

    def _prune_expired(self, now: float) -> None:
        """Remove IPs with no recent requests to prevent memory leaks."""
        expired = [
            ip for ip, ts in self.requests.items()
            if not ts or now - ts[-1] > self.window
        ]
        for ip in expired:
            del self.requests[ip]
        self._last_prune = now

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit scanner upload endpoint
        if request.url.path == "/api/scanner/upload":
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()

            # Periodic prune to prevent unbounded memory growth
            if now - self._last_prune > self._PRUNE_INTERVAL:
                self._prune_expired(now)

            # Safety valve: cap tracked IPs
            if len(self.requests) > self._MAX_TRACKED_IPS:
                self._prune_expired(now)
                if len(self.requests) > self._MAX_TRACKED_IPS:
                    logger.warning("Rate limiter: too many tracked IPs")
                    return JSONResponse(
                        status_code=503,
                        content={"detail": "Service temporarily overloaded."},
                    )

            # Clean old entries for this IP
            self.requests[client_ip] = [
                t for t in self.requests[client_ip] if now - t < self.window
            ]

            if len(self.requests[client_ip]) >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please try again later."},
                )

            self.requests[client_ip].append(now)

        return await call_next(request)


class GlobalErrorHandler(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return consistent JSON error."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(f"Unhandled error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "status_code": 500},
            )
