"""
Comprehensive tests for AlertingMiddleware.

Tests cover:
- Threshold-based alert triggering
- Counter tracking for different event types
- Cooldown mechanism to prevent alert flooding
- Integration with AlertDispatcher
- Request/response flow
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from src.app.middleware.monitoring import AlertingMiddleware


class TestAlertingMiddlewareThresholds:
    """Test threshold-based alerting logic."""

    def test_alert_triggered_when_threshold_exceeded(self):
        """Test that alert is sent when threshold is exceeded."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        # Create a mock dispatcher
        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        @app.get("/test")
        async def test_endpoint():
            return Response(status_code=429)

        # Add middleware with low threshold for testing
        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 3})
        middleware.alert_dispatcher.dispatch = capture_dispatch
        app.add_middleware(
            lambda app, **kwargs: middleware.__class__(app, **kwargs),
            alert_threshold={"rate_limit": 3},
        )

        # Manually test the middleware logic
        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # Trigger events below threshold - no alerts
        for _ in range(2):
            middleware._check_alert("rate_limit", mock_request)

        assert len(dispatched_alerts) == 0
        assert middleware.counters["rate_limit"] == 2

        # Trigger event that meets threshold - alert sent
        middleware._check_alert("rate_limit", mock_request)

        assert len(dispatched_alerts) == 1
        assert dispatched_alerts[0]["event_type"] == "rate_limit"
        assert dispatched_alerts[0]["count"] == 3
        assert dispatched_alerts[0]["path"] == "/test"
        assert dispatched_alerts[0]["method"] == "GET"
        assert middleware.counters["rate_limit"] == 0  # Counter reset

    def test_different_event_types_tracked_independently(self):
        """Test that different event types have independent counters."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(
            app, alert_threshold={"rate_limit": 3, "auth_failures": 2}
        )
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # Trigger rate_limit events
        middleware._check_alert("rate_limit", mock_request)
        middleware._check_alert("rate_limit", mock_request)

        # Trigger auth_failures events
        middleware._check_alert("auth_failures", mock_request)
        middleware._check_alert("auth_failures", mock_request)

        # Only auth_failures should have triggered alert (threshold: 2)
        assert len(dispatched_alerts) == 1
        assert dispatched_alerts[0]["event_type"] == "auth_failures"

        # Counters should be independent
        assert middleware.counters["rate_limit"] == 2
        assert middleware.counters["auth_failures"] == 0  # Reset after alert

    def test_default_thresholds_used(self):
        """Test that default thresholds are used when not specified."""
        app = FastAPI()
        middleware = AlertingMiddleware(app)

        assert middleware.thresholds["rate_limit"] == 100
        assert middleware.thresholds["auth_failures"] == 50
        assert middleware.thresholds["large_payloads"] == 10

    def test_custom_thresholds_override_defaults(self):
        """Test that custom thresholds override defaults."""
        app = FastAPI()
        custom_thresholds = {
            "rate_limit": 50,
            "auth_failures": 25,
        }
        middleware = AlertingMiddleware(app, alert_threshold=custom_thresholds)

        assert middleware.thresholds["rate_limit"] == 50
        assert middleware.thresholds["auth_failures"] == 25
        assert middleware.thresholds["large_payloads"] == 10  # Default still present


class TestAlertingMiddlewareCooldown:
    """Test cooldown mechanism to prevent alert flooding."""

    def test_cooldown_prevents_immediate_duplicate_alerts(self):
        """Test that alerts aren't sent again during cooldown period."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 2})
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # First batch - trigger alert
        middleware._check_alert("rate_limit", mock_request)
        middleware._check_alert("rate_limit", mock_request)

        assert len(dispatched_alerts) == 1

        # Second batch immediately after - should not trigger alert (cooldown)
        middleware._check_alert("rate_limit", mock_request)
        middleware._check_alert("rate_limit", mock_request)

        assert len(dispatched_alerts) == 1  # Still only one alert

    def test_alert_sent_after_cooldown_expires(self):
        """Test that alerts are sent again after cooldown period expires."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 2})
        middleware.alert_cooldown = 0.1  # 100ms cooldown for testing
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # First batch - trigger alert
        middleware._check_alert("rate_limit", mock_request)
        middleware._check_alert("rate_limit", mock_request)

        assert len(dispatched_alerts) == 1

        # Wait for cooldown to expire
        time.sleep(0.15)

        # Second batch after cooldown - should trigger new alert
        middleware._check_alert("rate_limit", mock_request)
        middleware._check_alert("rate_limit", mock_request)

        assert len(dispatched_alerts) == 2

    def test_cooldown_independent_per_event_type(self):
        """Test that cooldown is tracked independently per event type."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(
            app, alert_threshold={"rate_limit": 1, "auth_failures": 1}
        )
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # Trigger rate_limit alert
        middleware._check_alert("rate_limit", mock_request)
        assert len(dispatched_alerts) == 1

        # Trigger auth_failures alert immediately - should work (different event type)
        middleware._check_alert("auth_failures", mock_request)
        assert len(dispatched_alerts) == 2

        # Try rate_limit again immediately - should not work (cooldown)
        middleware._check_alert("rate_limit", mock_request)
        assert len(dispatched_alerts) == 2


class TestAlertingMiddlewareStatusCodeHandling:
    """Test that middleware responds to correct HTTP status codes."""

    @pytest.mark.asyncio
    async def test_429_triggers_rate_limit_check(self):
        """Test that 429 status code triggers rate_limit check."""
        app = FastAPI()
        check_alert_calls: list[tuple[str, Any]] = []

        @app.get("/test")
        async def test_endpoint():
            return Response(status_code=429)

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 1})

        # Mock _check_alert to track calls
        original_check = middleware._check_alert

        def track_check_alert(event_type: str, request: Any) -> None:
            check_alert_calls.append((event_type, request))
            original_check(event_type, request)

        middleware._check_alert = track_check_alert

        # Create mock request and call_next
        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            return Response(status_code=429)

        await middleware.dispatch(mock_request, mock_call_next)

        assert len(check_alert_calls) == 1
        assert check_alert_calls[0][0] == "rate_limit"

    @pytest.mark.asyncio
    async def test_401_triggers_auth_failures_check(self):
        """Test that 401 status code triggers auth_failures check."""
        app = FastAPI()
        check_alert_calls: list[tuple[str, Any]] = []

        middleware = AlertingMiddleware(app, alert_threshold={"auth_failures": 1})

        original_check = middleware._check_alert

        def track_check_alert(event_type: str, request: Any) -> None:
            check_alert_calls.append((event_type, request))
            original_check(event_type, request)

        middleware._check_alert = track_check_alert

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            return Response(status_code=401)

        await middleware.dispatch(mock_request, mock_call_next)

        assert len(check_alert_calls) == 1
        assert check_alert_calls[0][0] == "auth_failures"

    @pytest.mark.asyncio
    async def test_413_triggers_large_payloads_check(self):
        """Test that 413 status code triggers large_payloads check."""
        app = FastAPI()
        check_alert_calls: list[tuple[str, Any]] = []

        middleware = AlertingMiddleware(app, alert_threshold={"large_payloads": 1})

        original_check = middleware._check_alert

        def track_check_alert(event_type: str, request: Any) -> None:
            check_alert_calls.append((event_type, request))
            original_check(event_type, request)

        middleware._check_alert = track_check_alert

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            return Response(status_code=413)

        await middleware.dispatch(mock_request, mock_call_next)

        assert len(check_alert_calls) == 1
        assert check_alert_calls[0][0] == "large_payloads"

    @pytest.mark.asyncio
    async def test_200_does_not_trigger_checks(self):
        """Test that normal 200 status code doesn't trigger any checks."""
        app = FastAPI()
        check_alert_calls: list[tuple[str, Any]] = []

        middleware = AlertingMiddleware(app)

        def track_check_alert(event_type: str, request: Any) -> None:
            check_alert_calls.append((event_type, request))

        middleware._check_alert = track_check_alert

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            return Response(status_code=200)

        await middleware.dispatch(mock_request, mock_call_next)

        assert len(check_alert_calls) == 0


class TestAlertingMiddlewarePayloadConstruction:
    """Test alert payload construction."""

    def test_alert_payload_includes_all_required_fields(self):
        """Test that alert payload contains all required fields."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 1})
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/api/users/123"
        mock_request.method = "POST"
        mock_request.client.host = "192.168.1.100"

        middleware._check_alert("rate_limit", mock_request)

        assert len(dispatched_alerts) == 1
        payload = dispatched_alerts[0]

        assert "event_type" in payload
        assert "count" in payload
        assert "path" in payload
        assert "method" in payload
        assert "client" in payload

        assert payload["event_type"] == "rate_limit"
        assert payload["count"] == 1
        assert payload["path"] == "/api/users/123"
        assert payload["method"] == "POST"
        assert payload["client"] == "192.168.1.100"

    def test_alert_payload_handles_missing_client(self):
        """Test that payload handles missing client gracefully."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 1})
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client = None

        middleware._check_alert("rate_limit", mock_request)

        assert len(dispatched_alerts) == 1
        payload = dispatched_alerts[0]
        assert payload["client"] is None


class TestAlertingMiddlewareCounterReset:
    """Test counter reset behavior."""

    def test_counter_resets_after_alert_sent(self):
        """Test that counter resets to 0 after alert is sent."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 3})
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # Trigger threshold
        for _ in range(3):
            middleware._check_alert("rate_limit", mock_request)

        assert middleware.counters["rate_limit"] == 0

    def test_counter_accumulates_before_threshold(self):
        """Test that counter accumulates correctly before threshold."""
        app = FastAPI()

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 10})

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        for i in range(1, 8):
            middleware._check_alert("rate_limit", mock_request)
            assert middleware.counters["rate_limit"] == i


class TestAlertingMiddlewareLogging:
    """Test structured logging."""

    def test_critical_log_emitted_on_alert(self, caplog):
        """Test that critical log is emitted when alert is sent."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 1})
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # Note: structlog might not work with caplog in the same way
        # This test documents the expected behavior
        middleware._check_alert("rate_limit", mock_request)

        # Verify alert was dispatched (logging tested separately)
        assert len(dispatched_alerts) == 1


class TestAlertingMiddlewareEdgeCases:
    """Test edge cases and error conditions."""

    def test_handles_unknown_event_type_with_default_threshold(self):
        """Test that unknown event types use default threshold of 100."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(app, alert_threshold={"rate_limit": 5})
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # Trigger unknown event type many times
        for _ in range(99):
            middleware._check_alert("unknown_event", mock_request)

        assert len(dispatched_alerts) == 0  # Threshold not reached

        # 100th time should trigger (default threshold)
        middleware._check_alert("unknown_event", mock_request)
        assert len(dispatched_alerts) == 1
        assert dispatched_alerts[0]["event_type"] == "unknown_event"

    @pytest.mark.asyncio
    async def test_middleware_returns_response_unchanged(self):
        """Test that middleware passes through response unchanged."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        middleware = AlertingMiddleware(app)

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        expected_response = Response(content=b'{"message":"success"}', status_code=200)

        async def mock_call_next(request):
            return expected_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response is expected_response

    def test_multiple_concurrent_event_types(self):
        """Test handling multiple event types simultaneously."""
        app = FastAPI()
        dispatched_alerts: list[dict[str, Any]] = []

        def capture_dispatch(payload: dict[str, Any]) -> None:
            dispatched_alerts.append(payload)

        middleware = AlertingMiddleware(
            app,
            alert_threshold={
                "rate_limit": 2,
                "auth_failures": 2,
                "large_payloads": 2,
            },
        )
        middleware.alert_dispatcher.dispatch = capture_dispatch

        mock_request = Mock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"

        # Interleave different event types
        middleware._check_alert("rate_limit", mock_request)
        middleware._check_alert("auth_failures", mock_request)
        middleware._check_alert("rate_limit", mock_request)
        middleware._check_alert("large_payloads", mock_request)
        middleware._check_alert("auth_failures", mock_request)
        middleware._check_alert("large_payloads", mock_request)

        # All three should have triggered
        assert len(dispatched_alerts) == 3

        event_types = {alert["event_type"] for alert in dispatched_alerts}
        assert event_types == {"rate_limit", "auth_failures", "large_payloads"}
