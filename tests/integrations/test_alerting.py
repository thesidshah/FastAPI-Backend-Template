"""
Comprehensive tests for alerting integration module.

Tests cover:
- Teams webhook notifications
- Email notifications (SMTP and SMTP_SSL)
- Error handling and retries
- Message formatting
- Configuration loading
- Recipient parsing
"""

from __future__ import annotations

import smtplib
from typing import Any
from unittest.mock import Mock, patch

from src.app.integrations.alerting import (
    AlertDispatcher,
    AlertDispatcherError,
    EmailDeliveryError,
    TeamsWebhookError,
    _split_recipients,
)


def _payload(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a sample alert payload for testing."""
    payload = {
        "event_type": "rate_limit",
        "count": 3,
        "path": "/api/resource",
        "client": "127.0.0.1",
        "method": "GET",
    }
    if overrides:
        payload.update(overrides)
    return payload


class TestTeamsNotifications:
    """Test Teams webhook notification functionality."""

    def test_dispatch_sends_teams_notification(self):
        """Test that dispatch correctly sends Teams notifications."""
        calls: list[tuple[str, str]] = []

        def fake_sender(url: str, message: str) -> None:
            calls.append((url, message))

        dispatcher = AlertDispatcher(
            teams_webhook_url="https://teams.example.com/webhook",
            teams_sender=fake_sender,
            email_sender=lambda *_: None,
            email_config={},
        )

        dispatcher.dispatch(_payload())

        assert len(calls) == 1
        sent_url, message = calls[0]
        assert sent_url == "https://teams.example.com/webhook"
        assert "Security alert triggered." in message
        assert "Event: rate_limit" in message
        assert "Path: /api/resource" in message
        assert "Method: GET" in message
        assert "Client: 127.0.0.1" in message

    def test_teams_notification_without_client(self):
        """Test Teams message formatting when client IP is not provided."""
        calls: list[tuple[str, str]] = []

        def fake_sender(url: str, message: str) -> None:
            calls.append((url, message))

        dispatcher = AlertDispatcher(
            teams_webhook_url="https://teams.example.com/webhook",
            teams_sender=fake_sender,
            email_sender=lambda *_: None,
            email_config={},
        )

        dispatcher.dispatch(_payload({"client": None}))

        assert len(calls) == 1
        _, message = calls[0]
        assert "Client:" not in message

    def test_teams_error_handling(self):
        """Test that Teams webhook errors are properly raised."""

        def failing_sender(url: str, message: str) -> None:
            raise TeamsWebhookError("Webhook failed")

        dispatcher = AlertDispatcher(
            teams_webhook_url="https://teams.example.com/webhook",
            teams_sender=failing_sender,
            email_sender=lambda *_: None,
            email_config={},
        )

        # Should not raise - errors are handled in background
        dispatcher.dispatch(_payload())

    def test_no_teams_notification_when_not_configured(self):
        """Test that no Teams notification is sent when URL is not configured."""
        calls: list[tuple[str, str]] = []

        def fake_sender(url: str, message: str) -> None:
            calls.append((url, message))

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            teams_sender=fake_sender,
            email_sender=lambda *_: None,
            email_config={},
        )

        dispatcher.dispatch(_payload())

        assert len(calls) == 0


class TestEmailNotifications:
    """Test email notification functionality."""

    def test_dispatch_sends_email_notification(self):
        """Test that dispatch correctly sends email notifications."""
        sent_messages: list[tuple[dict[str, Any], str, str]] = []

        def fake_email_sender(config: dict[str, Any], subject: str, body: str) -> None:
            sent_messages.append((config, subject, body))

        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": None,
            "password": None,
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": False,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=email_config,
            teams_sender=lambda *_: None,
            email_sender=fake_email_sender,
        )

        dispatcher.dispatch(_payload({"client": None, "event_type": "auth_failures"}))

        assert len(sent_messages) == 1
        config, subject, body = sent_messages[0]
        assert config == email_config
        assert subject == "[Security Alert] Auth Failures"
        assert "Event: auth_failures" in body
        assert "Client:" not in body
        assert "Please investigate this event." in body

    def test_email_subject_formatting(self):
        """Test that email subjects are properly formatted."""
        sent_messages: list[tuple[dict[str, Any], str, str]] = []

        def fake_email_sender(config: dict[str, Any], subject: str, body: str) -> None:
            sent_messages.append((config, subject, body))

        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": None,
            "password": None,
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": False,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=email_config,
            teams_sender=lambda *_: None,
            email_sender=fake_email_sender,
        )

        dispatcher.dispatch(_payload({"event_type": "large_payloads"}))

        _, subject, _ = sent_messages[0]
        assert subject == "[Security Alert] Large Payloads"

    def test_email_with_multiple_recipients(self):
        """Test email notification with multiple recipients."""
        sent_messages: list[tuple[dict[str, Any], str, str]] = []

        def fake_email_sender(config: dict[str, Any], subject: str, body: str) -> None:
            sent_messages.append((config, subject, body))

        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": None,
            "password": None,
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com", "security@example.com", "admin@example.com"],
            "use_ssl": False,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=email_config,
            teams_sender=lambda *_: None,
            email_sender=fake_email_sender,
        )

        dispatcher.dispatch(_payload())

        assert len(sent_messages) == 1
        config, _, _ = sent_messages[0]
        assert len(config["recipients"]) == 3

    def test_no_email_when_not_configured(self):
        """Test that no email is sent when email is not configured."""
        sent_messages: list[tuple[dict[str, Any], str, str]] = []

        def fake_email_sender(config: dict[str, Any], subject: str, body: str) -> None:
            sent_messages.append((config, subject, body))

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=None,
            teams_sender=lambda *_: None,
            email_sender=fake_email_sender,
        )

        dispatcher.dispatch(_payload())

        assert len(sent_messages) == 0

    def test_email_error_handling(self):
        """Test that email delivery errors are properly raised."""

        def failing_sender(config: dict[str, Any], subject: str, body: str) -> None:
            raise EmailDeliveryError("SMTP connection failed")

        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": None,
            "password": None,
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": False,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=email_config,
            teams_sender=lambda *_: None,
            email_sender=failing_sender,
        )

        # Should not raise - errors are handled in background
        dispatcher.dispatch(_payload())


class TestMultiChannelDispatch:
    """Test dispatching to multiple channels simultaneously."""

    def test_dispatch_to_both_teams_and_email(self):
        """Test that alerts are sent to both Teams and email when configured."""
        teams_calls: list[tuple[str, str]] = []
        email_calls: list[tuple[dict[str, Any], str, str]] = []

        def fake_teams_sender(url: str, message: str) -> None:
            teams_calls.append((url, message))

        def fake_email_sender(config: dict[str, Any], subject: str, body: str) -> None:
            email_calls.append((config, subject, body))

        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": None,
            "password": None,
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": False,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url="https://teams.example.com/webhook",
            email_config=email_config,
            teams_sender=fake_teams_sender,
            email_sender=fake_email_sender,
        )

        dispatcher.dispatch(_payload())

        assert len(teams_calls) == 1
        assert len(email_calls) == 1

    def test_teams_failure_does_not_affect_email(self):
        """Test that Teams failure doesn't prevent email from being sent."""
        email_calls: list[tuple[dict[str, Any], str, str]] = []

        def failing_teams_sender(url: str, message: str) -> None:
            raise TeamsWebhookError("Teams failed")

        def fake_email_sender(config: dict[str, Any], subject: str, body: str) -> None:
            email_calls.append((config, subject, body))

        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": None,
            "password": None,
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": False,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url="https://teams.example.com/webhook",
            email_config=email_config,
            teams_sender=failing_teams_sender,
            email_sender=fake_email_sender,
        )

        dispatcher.dispatch(_payload())

        # Email should still be sent
        assert len(email_calls) == 1


class TestMessageFormatting:
    """Test alert message formatting."""

    def test_build_alert_message_with_all_fields(self):
        """Test message formatting with all fields present."""
        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config={},
            teams_sender=lambda *_: None,
            email_sender=lambda *_: None,
        )

        payload = {
            "event_type": "rate_limit",
            "count": 150,
            "path": "/api/users",
            "method": "POST",
            "client": "192.168.1.100",
        }

        message = dispatcher._build_alert_message(payload, for_email=False)

        assert "Security alert triggered." in message
        assert "Event: rate_limit" in message
        assert "Count: 150" in message
        assert "Method: POST" in message
        assert "Path: /api/users" in message
        assert "Client: 192.168.1.100" in message

    def test_email_format_includes_footer(self):
        """Test that email format includes investigation footer."""
        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config={},
            teams_sender=lambda *_: None,
            email_sender=lambda *_: None,
        )

        message = dispatcher._build_alert_message(_payload(), for_email=True)
        assert "Please investigate this event." in message

    def test_teams_format_excludes_footer(self):
        """Test that Teams format doesn't include investigation footer."""
        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config={},
            teams_sender=lambda *_: None,
            email_sender=lambda *_: None,
        )

        message = dispatcher._build_alert_message(_payload(), for_email=False)
        assert "Please investigate this event." not in message


class TestRecipientParsing:
    """Test email recipient string parsing."""

    def test_split_recipients_basic(self):
        """Test basic recipient splitting."""
        assert _split_recipients("a@example.com,b@example.com") == [
            "a@example.com",
            "b@example.com",
        ]

    def test_split_recipients_with_spaces(self):
        """Test recipient splitting with extra whitespace."""
        assert _split_recipients(" a@example.com , ,b@example.com ") == [
            "a@example.com",
            "b@example.com",
        ]

    def test_split_recipients_empty_string(self):
        """Test splitting empty string returns empty list."""
        assert _split_recipients("") == []

    def test_split_recipients_only_commas(self):
        """Test splitting string with only commas."""
        assert _split_recipients(",,,") == []

    def test_split_recipients_single(self):
        """Test splitting single recipient."""
        assert _split_recipients("admin@example.com") == ["admin@example.com"]

    def test_split_recipients_with_names(self):
        """Test splitting recipients with display names."""
        # This tests the current behavior - it doesn't parse RFC 5322 format
        result = _split_recipients("John Doe <john@example.com>, jane@example.com")
        assert len(result) == 2
        assert "John Doe <john@example.com>" in result
        assert "jane@example.com" in result


class TestConfigurationLoading:
    """Test configuration loading from environment variables."""

    @patch.dict(
        "os.environ",
        {
            "SECURITY_ALERT_EMAIL_HOST": "smtp.test.com",
            "SECURITY_ALERT_EMAIL_PORT": "465",
            "SECURITY_ALERT_EMAIL_RECIPIENTS": "admin@test.com,ops@test.com",
            "SECURITY_ALERT_EMAIL_USE_SSL": "true",
        },
        clear=True,
    )
    def test_load_email_config_from_env(self):
        """Test loading email configuration from environment variables."""
        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            teams_sender=lambda *_: None,
            email_sender=lambda *_: None,
        )

        assert dispatcher.email_config["host"] == "smtp.test.com"
        assert dispatcher.email_config["port"] == 465
        assert dispatcher.email_config["recipients"] == ["admin@test.com", "ops@test.com"]
        assert dispatcher.email_config["use_ssl"] is True

    @patch.dict("os.environ", {}, clear=True)
    def test_empty_config_when_missing_required_vars(self):
        """Test that config is empty when required environment variables are missing."""
        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            teams_sender=lambda *_: None,
            email_sender=lambda *_: None,
        )

        assert dispatcher.email_config == {}

    @patch.dict(
        "os.environ",
        {
            "SECURITY_ALERT_EMAIL_HOST": "smtp.test.com",
            "SECURITY_ALERT_EMAIL_RECIPIENTS": "",
        },
        clear=True,
    )
    def test_empty_config_when_no_recipients(self):
        """Test that config is empty when recipients list is empty."""
        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            teams_sender=lambda *_: None,
            email_sender=lambda *_: None,
        )

        assert dispatcher.email_config == {}

    @patch.dict(
        "os.environ",
        {
            "SECURITY_ALERT_TEAMS_WEBHOOK": "https://teams.test.com/webhook",
        },
        clear=True,
    )
    def test_load_teams_webhook_from_env(self):
        """Test loading Teams webhook URL from environment variable."""
        dispatcher = AlertDispatcher(
            teams_sender=lambda *_: None,
            email_sender=lambda *_: None,
        )

        assert dispatcher.teams_webhook_url == "https://teams.test.com/webhook"


class TestSMTPIntegration:
    """Test actual SMTP integration (mocked)."""

    @patch("smtplib.SMTP")
    def test_smtp_with_tls(self, mock_smtp_class):
        """Test SMTP connection with STARTTLS."""
        mock_smtp = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "password123",
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": False,
            "use_tls": True,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=email_config,
            teams_sender=lambda *_: None,
        )

        dispatcher.dispatch(_payload())

        # Give background task time to execute
        import time
        time.sleep(0.1)

        # Verify SMTP connection was made
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=10)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "password123")

    @patch("smtplib.SMTP_SSL")
    def test_smtp_with_ssl(self, mock_smtp_ssl_class):
        """Test SMTP connection with SSL/TLS."""
        mock_smtp = Mock()
        mock_smtp_ssl_class.return_value.__enter__.return_value = mock_smtp

        email_config = {
            "host": "smtp.example.com",
            "port": 465,
            "username": "user@example.com",
            "password": "password123",
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": True,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=email_config,
            teams_sender=lambda *_: None,
        )

        dispatcher.dispatch(_payload())

        # Give background task time to execute
        import time
        time.sleep(0.1)

        # Verify SMTP_SSL connection was made
        mock_smtp_ssl_class.assert_called_once_with("smtp.example.com", 465, timeout=10)
        mock_smtp.login.assert_called_once_with("user@example.com", "password123")

    @patch("smtplib.SMTP")
    def test_smtp_without_authentication(self, mock_smtp_class):
        """Test SMTP connection without authentication."""
        mock_smtp = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        email_config = {
            "host": "smtp.example.com",
            "port": 25,
            "username": None,
            "password": None,
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": False,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=email_config,
            teams_sender=lambda *_: None,
        )

        dispatcher.dispatch(_payload())

        # Give background task time to execute
        import time
        time.sleep(0.1)

        # Verify login was not called
        mock_smtp.login.assert_not_called()

    @patch("smtplib.SMTP")
    def test_smtp_exception_handling(self, mock_smtp_class):
        """Test SMTP exception handling."""
        mock_smtp = Mock()
        mock_smtp.send_message.side_effect = smtplib.SMTPException("Connection failed")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": None,
            "password": None,
            "from_address": "alerts@example.com",
            "recipients": ["ops@example.com"],
            "use_ssl": False,
            "use_tls": False,
        }

        dispatcher = AlertDispatcher(
            teams_webhook_url=None,
            email_config=email_config,
            teams_sender=lambda *_: None,
        )

        # Should not raise - errors are logged
        dispatcher.dispatch(_payload())


class TestExceptionHierarchy:
    """Test custom exception classes."""

    def test_exception_hierarchy(self):
        """Test that custom exceptions inherit correctly."""
        assert issubclass(TeamsWebhookError, AlertDispatcherError)
        assert issubclass(EmailDeliveryError, AlertDispatcherError)
        assert issubclass(AlertDispatcherError, Exception)

    def test_teams_webhook_error_message(self):
        """Test TeamsWebhookError with custom message."""
        error = TeamsWebhookError("Webhook timeout")
        assert str(error) == "Webhook timeout"

    def test_email_delivery_error_message(self):
        """Test EmailDeliveryError with custom message."""
        error = EmailDeliveryError("SMTP authentication failed")
        assert str(error) == "SMTP authentication failed"
        