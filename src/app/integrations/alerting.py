"""
Alerting integrations for security events.

This module provides a unified interface for dispatching security alerts to multiple
notification channels including Microsoft Teams and email. It supports async execution
to avoid blocking the main application event loop.

Example:
    dispatcher = AlertDispatcher()
    dispatcher.dispatch({
        "event_type": "rate_limit",
        "count": 100,
        "path": "/api/resource",
        "client": "192.168.1.1",
        "method": "POST"
    })
"""

from __future__ import annotations

import asyncio
import json
import os
import smtplib
from email.message import EmailMessage
from functools import partial
from typing import Any, Callable, Optional
from urllib.request import Request, urlopen

import structlog

logger = structlog.get_logger(__name__)


class AlertDispatcherError(Exception):
    """Base exception for alert dispatcher errors."""


class TeamsWebhookError(AlertDispatcherError):
    """Error sending Teams webhook notification."""


class EmailDeliveryError(AlertDispatcherError):
    """Error sending email notification."""


class AlertDispatcher:
    """
    Dispatch security alerts to external systems (e.g. Teams, email).

    This class handles sending security alerts through multiple channels with
    non-blocking execution. It supports dependency injection for testing.

    Args:
        teams_webhook_url: Microsoft Teams incoming webhook URL. Falls back to
            SECURITY_ALERT_TEAMS_WEBHOOK environment variable.
        email_config: Email configuration dict. If None, loads from environment.
        teams_sender: Optional callable for sending Teams messages (for testing).
        email_sender: Optional callable for sending emails (for testing).

    Example:
        >>> dispatcher = AlertDispatcher(
        ...     teams_webhook_url="https://teams.webhook.url",
        ...     email_config={"host": "smtp.example.com", ...}
        ... )
        >>> dispatcher.dispatch({"event_type": "rate_limit", ...})
    """

    def __init__(
        self,
        *,
        teams_webhook_url: str | None = None,
        email_config: Optional[dict[str, Any]] = None,
        teams_sender: Optional[Callable[[str, str], None]] = None,
        email_sender: Optional[Callable[[dict[str, Any], str, str], None]] = None,
    ):
        self.teams_webhook_url = teams_webhook_url or os.getenv(
            "SECURITY_ALERT_TEAMS_WEBHOOK"
        )

        self.email_config = email_config or self._load_email_config()
        self._teams_sender = teams_sender or self._post_to_teams_webhook
        self._email_sender = email_sender or self._send_email_notification

    def dispatch(self, payload: dict[str, Any]) -> None:
        """
        Dispatch alert payload to configured integrations.

        Sends alerts to all configured channels (Teams, email) in parallel without
        blocking. Errors in individual channels are logged but don't prevent other
        channels from receiving the alert.

        Args:
            payload: Alert data containing:
                - event_type: Type of security event (e.g., "rate_limit")
                - count: Number of occurrences
                - path: Request path that triggered the alert
                - method: HTTP method
                - client: Client IP address (optional)

        Example:
            >>> dispatcher.dispatch({
            ...     "event_type": "rate_limit",
            ...     "count": 150,
            ...     "path": "/api/users",
            ...     "method": "POST",
            ...     "client": "192.168.1.1"
            ... })
        """
        if self.teams_webhook_url:
            message = self._build_alert_message(payload, for_email=False)
            self._run_background_task(
                self._teams_sender, self.teams_webhook_url, message
            )

        if self.email_config:
            subject = self._build_subject(payload["event_type"])
            body = self._build_alert_message(payload, for_email=True)
            self._run_background_task(
                self._email_sender, dict(self.email_config), subject, body
            )

    def _build_subject(self, event_type: str) -> str:
        """
        Build email subject from event type.

        Args:
            event_type: Event identifier (e.g., "rate_limit", "auth_failures")

        Returns:
            Formatted subject line
        """
        return f"[Security Alert] {event_type.replace('_', ' ').title()}"

    def _build_alert_message(self, payload: dict[str, Any], for_email: bool) -> str:
        """
        Create alert message body from payload.

        Args:
            payload: Alert data dictionary
            for_email: Whether this is for email (adds footer) or Teams

        Returns:
            Formatted message string
        """
        lines = [
            "Security alert triggered.",
            f"Event: {payload['event_type']}",
            f"Count: {payload['count']}",
            f"Method: {payload['method']}",
            f"Path: {payload['path']}",
        ]

        if payload.get("client"):
            lines.append(f"Client: {payload['client']}")

        if for_email:
            lines.extend(["", "Please investigate this event."])

        return "\n".join(lines)

    def _run_background_task(self, func: Callable, *args, **kwargs) -> None:
        """
        Run blocking alert integrations without stalling the event loop.

        If called within an async context, submits the function to a thread pool.
        Otherwise, executes synchronously.

        Args:
            func: The function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Not in async context, run synchronously
            func(*args, **kwargs)
            return

        # In async context, run in thread pool executor
        loop.run_in_executor(None, partial(func, *args, **kwargs))

    def _post_to_teams_webhook(self, webhook_url: str, message: str) -> None:
        """
        Send alert notification to Microsoft Teams via incoming webhook.

        Args:
            webhook_url: Teams incoming webhook URL
            message: Alert message text to send

        Raises:
            TeamsWebhookError: If the webhook request fails
        """
        payload = json.dumps({"text": message}).encode("utf-8")
        request = Request(
            webhook_url, data=payload, headers={"Content-Type": "application/json"}
        )

        try:
            with urlopen(request, timeout=5) as response:  # noqa: S310
                if response.status != 200:
                    error_body = response.read().decode("utf-8")
                    raise TeamsWebhookError(
                        f"Teams webhook returned {response.status}: {error_body}"
                    )
                response.read()
        except TeamsWebhookError:
            raise
        except OSError as exc:
            # Network errors, timeouts, etc.
            logger.error("alerting.teams_failed", error=str(exc), webhook_url=webhook_url)
            raise TeamsWebhookError(f"Failed to send Teams notification: {exc}") from exc
        except Exception as exc:
            # Catch-all for unexpected errors
            logger.error(
                "alerting.teams_unexpected_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise TeamsWebhookError(f"Unexpected error sending Teams notification: {exc}") from exc

    def _send_email_notification(
        self, config: dict[str, Any], subject: str, body: str
    ) -> None:
        """
        Send alert notification via email using SMTP.

        Args:
            config: Email configuration containing host, port, credentials, etc.
            subject: Email subject line
            body: Email body text

        Raises:
            EmailDeliveryError: If email sending fails
        """
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = config["from_address"]
        msg["To"] = ", ".join(config["recipients"])
        msg.set_content(body)

        try:
            if config["use_ssl"]:
                with smtplib.SMTP_SSL(
                    config["host"], config["port"], timeout=10
                ) as smtp:
                    self._smtp_login_if_needed(smtp, config)
                    smtp.send_message(msg)
                    return

            with smtplib.SMTP(config["host"], config["port"], timeout=10) as smtp:
                if config["use_tls"]:
                    smtp.starttls()
                self._smtp_login_if_needed(smtp, config)
                smtp.send_message(msg)
        except smtplib.SMTPException as exc:
            # SMTP-specific errors (auth, connection, etc.)
            logger.error(
                "alerting.email_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                host=config["host"],
            )
            raise EmailDeliveryError(f"SMTP error sending email: {exc}") from exc
        except OSError as exc:
            # Network errors, timeouts, etc.
            logger.error(
                "alerting.email_network_error",
                error=str(exc),
                host=config["host"],
            )
            raise EmailDeliveryError(f"Network error sending email: {exc}") from exc
        except Exception as exc:
            # Catch-all for unexpected errors
            logger.error(
                "alerting.email_unexpected_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise EmailDeliveryError(f"Unexpected error sending email: {exc}") from exc

    def _smtp_login_if_needed(
        self, smtp: smtplib.SMTP, config: dict[str, Any]
    ) -> None:
        """
        Authenticate with SMTP server when credentials are provided.

        Args:
            smtp: SMTP connection object
            config: Configuration dict containing optional username and password
        """
        username = config.get("username")
        password = config.get("password")

        if username and password:
            smtp.login(username, password)

    def _load_email_config(self) -> dict[str, Any]:
        """
        Load email settings from environment variables.

        Returns:
            Email configuration dict, or empty dict if required settings are missing.

        Environment Variables:
            SECURITY_ALERT_EMAIL_HOST: SMTP server hostname (required)
            SECURITY_ALERT_EMAIL_PORT: SMTP port (default: 587)
            SECURITY_ALERT_EMAIL_USERNAME: SMTP username (optional)
            SECURITY_ALERT_EMAIL_PASSWORD: SMTP password (optional)
            SECURITY_ALERT_EMAIL_FROM: From address (optional)
            SECURITY_ALERT_EMAIL_RECIPIENTS: Comma-separated recipients (required)
            SECURITY_ALERT_EMAIL_USE_SSL: Use SSL/TLS (default: false)
            SECURITY_ALERT_EMAIL_USE_TLS: Use STARTTLS (default: true)
        """
        host = os.getenv("SECURITY_ALERT_EMAIL_HOST")
        recipients_raw = os.getenv("SECURITY_ALERT_EMAIL_RECIPIENTS", "")

        recipients = _split_recipients(recipients_raw)

        if not host or not recipients:
            return {}

        use_ssl = os.getenv("SECURITY_ALERT_EMAIL_USE_SSL", "false").lower()
        use_tls = os.getenv("SECURITY_ALERT_EMAIL_USE_TLS", "true").lower()

        return {
            "host": host,
            "port": int(os.getenv("SECURITY_ALERT_EMAIL_PORT", "587")),
            "username": os.getenv("SECURITY_ALERT_EMAIL_USERNAME") or None,
            "password": os.getenv("SECURITY_ALERT_EMAIL_PASSWORD") or None,
            "from_address": os.getenv(
                "SECURITY_ALERT_EMAIL_FROM",
                os.getenv("SECURITY_ALERT_EMAIL_USERNAME", "alerts@example.com"),
            ),
            "recipients": recipients,
            "use_ssl": use_ssl in {"1", "true", "yes", "on"},
            "use_tls": use_tls not in {"0", "false", "no", "off"},
        }


def _split_recipients(value: str) -> list[str]:
    """
    Split a comma-separated list of email recipients.

    Args:
        value: Comma-separated email addresses

    Returns:
        List of trimmed email addresses, with empty strings filtered out

    Example:
        >>> _split_recipients("user1@example.com, user2@example.com")
        ['user1@example.com', 'user2@example.com']
        >>> _split_recipients("  admin@example.com  ,,  ops@example.com  ")
        ['admin@example.com', 'ops@example.com']
    """
    return [addr.strip() for addr in value.split(",") if addr.strip()]
