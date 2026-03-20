"""Unit tests for application middleware."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from backend.app.middleware import (
    GlobalExceptionMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)


def create_test_app(middleware_classes=None, **middleware_kwargs):
    """Create a minimal FastAPI app with specified middleware."""
    app = FastAPI()

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/error")
    async def error():
        raise ValueError("test error")

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/v1/data")
    async def api_data():
        return {"data": [1, 2, 3]}

    if middleware_classes:
        for cls in middleware_classes:
            if cls == RateLimitMiddleware:
                app.add_middleware(cls, **middleware_kwargs)
            else:
                app.add_middleware(cls)

    return app


class TestGlobalExceptionMiddleware:
    """Test unhandled exception catching."""

    def setup_method(self):
        self.app = create_test_app([GlobalExceptionMiddleware])
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_normal_request_passes_through(self):
        response = self.client.get("/ok")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_unhandled_exception_returns_500_json(self):
        response = self.client.get("/error")
        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Internal server error"
        assert body["type"] == "ValueError"

    def test_404_passes_through(self):
        response = self.client.get("/nonexistent")
        assert response.status_code == 404


class TestRateLimitMiddleware:
    """Test per-IP rate limiting."""

    def test_requests_within_limit_succeed(self):
        app = create_test_app([RateLimitMiddleware], requests_per_minute=10)
        client = TestClient(app)
        for _ in range(10):
            response = client.get("/ok")
            assert response.status_code == 200

    def test_exceeding_limit_returns_429(self):
        app = create_test_app([RateLimitMiddleware], requests_per_minute=3)
        client = TestClient(app)
        # First 3 should succeed
        for _ in range(3):
            response = client.get("/ok")
            assert response.status_code == 200
        # 4th should be rate limited
        response = client.get("/ok")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
        assert "Retry-After" in response.headers

    def test_health_endpoint_exempt(self):
        app = create_test_app([RateLimitMiddleware], requests_per_minute=2)
        client = TestClient(app)
        # Exhaust the limit
        for _ in range(2):
            client.get("/ok")
        # Health should still work
        response = client.get("/health")
        assert response.status_code == 200

    def test_api_v1_endpoint_exempt(self):
        app = create_test_app([RateLimitMiddleware], requests_per_minute=2)
        client = TestClient(app)
        for _ in range(2):
            client.get("/ok")
        response = client.get("/api/v1")
        assert response.status_code == 404  # No handler, but not rate limited


class TestRequestLoggingMiddleware:
    """Test request logging behavior."""

    def test_logs_api_requests(self):
        app = create_test_app([RequestLoggingMiddleware])
        client = TestClient(app)
        with patch("backend.app.middleware.logger") as mock_logger:
            client.get("/api/v1/data")
            mock_logger.info.assert_called_once()
            log_msg = mock_logger.info.call_args[0][0]
            assert "GET" in log_msg
            assert "/api/v1/data" in log_msg
            assert "200" in log_msg
            assert "ms" in log_msg

    def test_skips_non_api_requests(self):
        app = create_test_app([RequestLoggingMiddleware])
        client = TestClient(app)
        with patch("backend.app.middleware.logger") as mock_logger:
            client.get("/ok")
            mock_logger.info.assert_not_called()
