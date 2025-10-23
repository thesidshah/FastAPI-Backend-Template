# Alerting Integrations

The alerting system provides real-time notifications for critical security events through multiple channels including Microsoft Teams and email. It integrates seamlessly with the security middleware to automatically dispatch alerts when threat thresholds are exceeded.

## Overview

When enabled, the `AlertDispatcher` automatically sends notifications to configured channels without blocking your application's request/response cycle. All integrations run in background threads to ensure minimal performance impact.

## Features

- **Multi-channel notifications**: Send alerts to Teams and email simultaneously
- **Non-blocking execution**: Background processing ensures no request latency
- **Flexible configuration**: Environment-based configuration for easy deployment
- **Robust error handling**: Individual channel failures don't affect other channels
- **Structured logging**: All failures are logged for debugging and monitoring

## Quick Start

### Microsoft Teams Setup

1. Create an incoming webhook in your Teams channel:
   - Navigate to your Teams channel
   - Click **•••** (More options) → **Connectors**
   - Search for "Incoming Webhook" and click **Configure**
   - Name your webhook (e.g., "Security Alerts") and upload an icon (optional)
   - Copy the webhook URL

2. Set the environment variable:
   ```bash
   export SECURITY_ALERT_TEAMS_WEBHOOK="https://your-org.webhook.office.com/webhookb2/..."
   ```

### Email Setup

1. Configure your SMTP settings via environment variables:

   ```bash
   # Required settings
   export SECURITY_ALERT_EMAIL_HOST="smtp.gmail.com"
   export SECURITY_ALERT_EMAIL_RECIPIENTS="security@example.com,ops@example.com"

   # Optional authentication (required for most SMTP servers)
   export SECURITY_ALERT_EMAIL_USERNAME="alerts@example.com"
   export SECURITY_ALERT_EMAIL_PASSWORD="your-app-password"

   # Optional settings with defaults
   export SECURITY_ALERT_EMAIL_PORT="587"  # Default: 587
   export SECURITY_ALERT_EMAIL_FROM="alerts@example.com"  # Default: username
   export SECURITY_ALERT_EMAIL_USE_TLS="true"  # Default: true
   export SECURITY_ALERT_EMAIL_USE_SSL="false"  # Default: false
   ```

2. For Gmail users:
   - Use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password
   - Enable "Less secure app access" if using a regular password (not recommended)

## Configuration Reference

### Microsoft Teams Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECURITY_ALERT_TEAMS_WEBHOOK` | Yes | Incoming webhook URL from Teams channel connector |

### Email Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECURITY_ALERT_EMAIL_HOST` | Yes | - | SMTP server hostname or IP address |
| `SECURITY_ALERT_EMAIL_RECIPIENTS` | Yes | - | Comma-separated list of recipient email addresses |
| `SECURITY_ALERT_EMAIL_PORT` | No | `587` | SMTP server port (587 for TLS, 465 for SSL, 25 for plain) |
| `SECURITY_ALERT_EMAIL_USERNAME` | No | - | SMTP authentication username |
| `SECURITY_ALERT_EMAIL_PASSWORD` | No | - | SMTP authentication password |
| `SECURITY_ALERT_EMAIL_FROM` | No | Username or `alerts@example.com` | Sender email address |
| `SECURITY_ALERT_EMAIL_USE_SSL` | No | `false` | Use SSL/TLS (SMTPS on port 465) |
| `SECURITY_ALERT_EMAIL_USE_TLS` | No | `true` | Use STARTTLS (upgrade plain SMTP to TLS) |

### Connection Modes

The email integration supports three SMTP connection modes:

1. **STARTTLS (Recommended)**: Plain SMTP upgraded to TLS
   ```bash
   SECURITY_ALERT_EMAIL_PORT=587
   SECURITY_ALERT_EMAIL_USE_TLS=true
   SECURITY_ALERT_EMAIL_USE_SSL=false
   ```

2. **SSL/TLS (SMTPS)**: Encrypted from the start
   ```bash
   SECURITY_ALERT_EMAIL_PORT=465
   SECURITY_ALERT_EMAIL_USE_SSL=true
   SECURITY_ALERT_EMAIL_USE_TLS=false
   ```

3. **Plain SMTP (Not Recommended)**: Unencrypted connection
   ```bash
   SECURITY_ALERT_EMAIL_PORT=25
   SECURITY_ALERT_EMAIL_USE_TLS=false
   SECURITY_ALERT_EMAIL_USE_SSL=false
   ```

## Integration with Middleware

The `AlertingMiddleware` automatically triggers alerts when security thresholds are exceeded. No additional code is required beyond setting environment variables.

### Example: Enable Alerting in FastAPI

```python
from fastapi import FastAPI
from src.app.middleware.monitoring import AlertingMiddleware

app = FastAPI()

# Add alerting middleware with custom thresholds
app.add_middleware(
    AlertingMiddleware,
    alert_threshold={
        "rate_limit": 100,      # Alert after 100 rate limit hits
        "auth_failures": 50,    # Alert after 50 authentication failures
        "large_payloads": 10,   # Alert after 10 oversized payload attempts
    }
)
```

### Alert Triggers

Alerts are automatically sent when these HTTP response codes exceed configured thresholds:

| Status Code | Event Type | Default Threshold | Description |
|-------------|------------|-------------------|-------------|
| 429 | `rate_limit` | 100 | Too many requests from a client |
| 401 | `auth_failures` | 50 | Authentication failures |
| 413 | `large_payloads` | 10 | Request payload too large |

### Alert Cooldown

After an alert is sent, the system waits 5 minutes (300 seconds) before sending another alert for the same event type. This prevents alert flooding during ongoing incidents.

## Programmatic Usage

You can also use the `AlertDispatcher` directly in your application code:

```python
from src.app.integrations.alerting import AlertDispatcher

# Initialize dispatcher (loads config from environment)
dispatcher = AlertDispatcher()

# Send custom alert
dispatcher.dispatch({
    "event_type": "suspicious_activity",
    "count": 25,
    "path": "/admin/users",
    "method": "DELETE",
    "client": "192.168.1.100"
})
```

### Alert Payload Schema

```python
{
    "event_type": str,      # Event identifier (e.g., "rate_limit", "auth_failures")
    "count": int,           # Number of occurrences that triggered the alert
    "path": str,            # Request path or resource affected
    "method": str,          # HTTP method (GET, POST, etc.)
    "client": str | None,   # Client IP address (optional)
}
```

## Testing

### Unit Testing with Dependency Injection

The `AlertDispatcher` supports dependency injection for testing:

```python
from src.app.integrations.alerting import AlertDispatcher

def test_my_alert_logic():
    sent_alerts = []

    def fake_teams_sender(url: str, message: str) -> None:
        sent_alerts.append(("teams", url, message))

    def fake_email_sender(config: dict, subject: str, body: str) -> None:
        sent_alerts.append(("email", subject, body))

    dispatcher = AlertDispatcher(
        teams_webhook_url="https://test.webhook.url",
        email_config={"host": "smtp.test.com", ...},
        teams_sender=fake_teams_sender,
        email_sender=fake_email_sender,
    )

    dispatcher.dispatch({
        "event_type": "test_event",
        "count": 1,
        "path": "/test",
        "method": "GET",
        "client": "127.0.0.1"
    })

    assert len(sent_alerts) == 2
```

### Integration Testing

For integration tests, you can use a real SMTP server or mock SMTP service:

```python
import smtplib
from unittest.mock import patch

@patch("smtplib.SMTP")
def test_email_integration(mock_smtp_class):
    mock_smtp = Mock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp

    dispatcher = AlertDispatcher(
        email_config={
            "host": "smtp.test.com",
            "port": 587,
            "username": "user@test.com",
            "password": "password",
            "from_address": "alerts@test.com",
            "recipients": ["ops@test.com"],
            "use_ssl": False,
            "use_tls": True,
        }
    )

    dispatcher.dispatch({...})

    # Verify SMTP interactions
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once()
```

## Error Handling

### Exception Hierarchy

```python
AlertDispatcherError          # Base exception
├── TeamsWebhookError         # Teams webhook failures
└── EmailDeliveryError        # Email delivery failures
```

### Logging

All errors are logged using structured logging:

```python
# Teams webhook failure
logger.error("alerting.teams_failed", error=str(exc), webhook_url=url)

# Email delivery failure
logger.error("alerting.email_failed", error=str(exc), host=smtp_host)

# Unexpected errors
logger.error("alerting.teams_unexpected_error", error=str(exc), error_type=type_name)
```

### Graceful Degradation

- Individual channel failures don't affect other channels
- All exceptions are caught and logged, never propagated
- Background execution prevents application impact
- Failed alerts don't retry automatically (implement retry logic externally if needed)

## Common SMTP Providers

### Gmail

```bash
SECURITY_ALERT_EMAIL_HOST=smtp.gmail.com
SECURITY_ALERT_EMAIL_PORT=587
SECURITY_ALERT_EMAIL_USE_TLS=true
SECURITY_ALERT_EMAIL_USERNAME=your-email@gmail.com
SECURITY_ALERT_EMAIL_PASSWORD=your-app-password  # Use App Password!
```

### Office 365

```bash
SECURITY_ALERT_EMAIL_HOST=smtp.office365.com
SECURITY_ALERT_EMAIL_PORT=587
SECURITY_ALERT_EMAIL_USE_TLS=true
SECURITY_ALERT_EMAIL_USERNAME=your-email@company.com
SECURITY_ALERT_EMAIL_PASSWORD=your-password
```

### SendGrid

```bash
SECURITY_ALERT_EMAIL_HOST=smtp.sendgrid.net
SECURITY_ALERT_EMAIL_PORT=587
SECURITY_ALERT_EMAIL_USE_TLS=true
SECURITY_ALERT_EMAIL_USERNAME=apikey
SECURITY_ALERT_EMAIL_PASSWORD=your-sendgrid-api-key
```

### AWS SES

```bash
SECURITY_ALERT_EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
SECURITY_ALERT_EMAIL_PORT=587
SECURITY_ALERT_EMAIL_USE_TLS=true
SECURITY_ALERT_EMAIL_USERNAME=your-ses-smtp-username
SECURITY_ALERT_EMAIL_PASSWORD=your-ses-smtp-password
```

### Mailgun

```bash
SECURITY_ALERT_EMAIL_HOST=smtp.mailgun.org
SECURITY_ALERT_EMAIL_PORT=587
SECURITY_ALERT_EMAIL_USE_TLS=true
SECURITY_ALERT_EMAIL_USERNAME=postmaster@your-domain.mailgun.org
SECURITY_ALERT_EMAIL_PASSWORD=your-mailgun-smtp-password
```

## Troubleshooting

### No Alerts Received

1. **Check environment variables are set correctly**
   ```bash
   env | grep SECURITY_ALERT
   ```

2. **Verify middleware is enabled**
   ```python
   # Ensure AlertingMiddleware is added to your app
   app.add_middleware(AlertingMiddleware)
   ```

3. **Check application logs for errors**
   ```bash
   # Look for alerting-related log entries
   grep "alerting\." application.log
   ```

4. **Verify thresholds are being exceeded**
   - Default thresholds may be too high for testing
   - Lower thresholds temporarily for testing:
     ```python
     app.add_middleware(AlertingMiddleware, alert_threshold={"rate_limit": 5})
     ```

### Teams Webhook Errors

1. **Invalid webhook URL**: Ensure URL is copied correctly from Teams
2. **Webhook expired**: Webhooks can expire; create a new one
3. **Network connectivity**: Test webhook with curl:
   ```bash
   curl -H "Content-Type: application/json" \
        -d '{"text":"Test message"}' \
        $SECURITY_ALERT_TEAMS_WEBHOOK
   ```

### Email Delivery Errors

1. **Authentication failures**
   - Verify username/password are correct
   - For Gmail, use App Password instead of regular password
   - Check if 2FA is enabled and configured correctly

2. **Connection timeouts**
   - Verify SMTP host and port are correct
   - Check firewall rules allow outbound SMTP connections
   - Try telnet to test connectivity: `telnet smtp.example.com 587`

3. **SSL/TLS errors**
   - Ensure `USE_SSL` and `USE_TLS` settings match your provider
   - Port 587 typically uses STARTTLS (USE_TLS=true)
   - Port 465 typically uses SSL/TLS (USE_SSL=true)

4. **Recipient errors**
   - Verify email addresses are valid
   - Check for typos in recipient list
   - Ensure recipients aren't blocking your sender address

## Best Practices

1. **Use dedicated email address**: Create a dedicated sender address for alerts (e.g., `security-alerts@example.com`)

2. **Set up email filtering**: Configure email rules to route alerts to appropriate folders/channels

3. **Monitor alert volume**: Set up dashboards to track alert frequency and prevent alert fatigue

4. **Test regularly**: Periodically test alert delivery to ensure configuration remains valid

5. **Secure credentials**: Use environment variables or secret management systems (never hardcode credentials)

6. **Configure appropriate thresholds**: Balance between catching threats and avoiding false positives

7. **Document runbooks**: Create response procedures for each alert type

8. **Implement escalation**: Use multiple recipient addresses with different escalation levels

## Security Considerations

- **Credentials**: Never commit SMTP credentials or webhook URLs to version control
- **Encryption**: Always use TLS/SSL for SMTP connections (disable plain SMTP in production)
- **Webhook validation**: Teams webhooks are public URLs; consider implementing additional validation
- **Rate limiting**: The built-in cooldown prevents alert flooding
- **Sensitive data**: Avoid including sensitive data (passwords, tokens) in alert messages
- **Access control**: Limit who can view alert channels to authorized personnel

## Performance Impact

The alerting system is designed for minimal performance impact:

- **Background execution**: All notifications run in thread pool executors
- **Non-blocking**: Request/response cycle is never blocked by alert delivery
- **Timeout protection**: Both Teams and email have connection timeouts (5s and 10s respectively)
- **Memory efficient**: No queuing or buffering of alerts
- **CPU overhead**: Minimal; only string formatting and network I/O

## Further Reading

- [Microsoft Teams Incoming Webhooks](https://docs.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook)
- [SMTP Protocol](https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol)
- [Python smtplib Documentation](https://docs.python.org/3/library/smtplib.html)
- [FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)
