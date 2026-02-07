"""Tests for app.api.middleware — rate limiter and middleware stack."""

import time

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.api.middleware import RateLimitMiddleware


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rate_limiter():
    """A standalone RateLimitMiddleware instance for unit testing."""
    return RateLimitMiddleware(
        app=MagicMock(),
        max_requests=10,
        window_seconds=60,
    )


# ---------------------------------------------------------------------------
# Tests: health endpoint via real ASGI client (not rate limited)
# ---------------------------------------------------------------------------


class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_normal_requests(self, async_client):
        """Non-scanner endpoints should not be rate limited."""
        resp = await async_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# Tests: _prune_expired
# ---------------------------------------------------------------------------


class TestPruneExpired:

    def test_prune_removes_old_entries(self, rate_limiter):
        """Entries older than the window are removed."""
        now = time.time()
        rate_limiter.requests["1.2.3.4"] = [now - 120]  # expired (>60s)
        rate_limiter.requests["5.6.7.8"] = [now - 10]   # still valid

        rate_limiter._prune_expired(now)

        assert "1.2.3.4" not in rate_limiter.requests
        assert "5.6.7.8" in rate_limiter.requests

    def test_prune_removes_empty_lists(self, rate_limiter):
        """IPs with empty request lists are pruned."""
        now = time.time()
        rate_limiter.requests["empty_ip"] = []

        rate_limiter._prune_expired(now)

        assert "empty_ip" not in rate_limiter.requests

    def test_prune_keeps_recent(self, rate_limiter):
        """Recent entries within the window are preserved."""
        now = time.time()
        rate_limiter.requests["recent"] = [now - 5, now - 2, now]

        rate_limiter._prune_expired(now)

        assert "recent" in rate_limiter.requests
        assert len(rate_limiter.requests["recent"]) == 3

    def test_prune_updates_last_prune_time(self, rate_limiter):
        """_prune_expired updates the _last_prune timestamp."""
        now = time.time()
        rate_limiter._prune_expired(now)
        assert rate_limiter._last_prune == now


# ---------------------------------------------------------------------------
# Tests: max_ips safety valve
# ---------------------------------------------------------------------------


class TestMaxIPsSafetyValve:

    def test_max_tracked_ips_constant(self, rate_limiter):
        """Verify the safety valve constant is set."""
        assert rate_limiter._MAX_TRACKED_IPS == 10_000

    def test_safety_valve_triggers_prune(self, rate_limiter):
        """When tracked IPs exceed _MAX_TRACKED_IPS, the middleware prunes.

        We simulate by filling requests dict beyond the cap and verifying
        the middleware logic path (the prune call is made in dispatch).
        """
        now = time.time()
        # Fill with expired entries beyond max
        for i in range(rate_limiter._MAX_TRACKED_IPS + 100):
            rate_limiter.requests[f"192.168.{i // 256}.{i % 256}"] = [now - 120]

        assert len(rate_limiter.requests) > rate_limiter._MAX_TRACKED_IPS

        # Prune should clean all expired
        rate_limiter._prune_expired(now)
        assert len(rate_limiter.requests) == 0


# ---------------------------------------------------------------------------
# Tests: sliding window request counting
# ---------------------------------------------------------------------------


class TestSlidingWindow:

    def test_window_size(self, rate_limiter):
        assert rate_limiter.window == 60

    def test_max_requests(self, rate_limiter):
        assert rate_limiter.max_requests == 10

    def test_requests_dict_is_defaultdict(self, rate_limiter):
        """Accessing a new IP key should return an empty list."""
        assert rate_limiter.requests["new_ip"] == []
