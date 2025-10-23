
# Testing Lifespan Events

This document explains the process of adding tests for the lifespan events in the FastAPI application.

## Initial State

The application's lifespan events, specifically the startup and shutdown logging, were not covered by any tests. The existing test files, `tests/test_health.py` and `tests/test_security_middleware.py`, did not include checks for these events.

## Creating a New Test File

A new test file, `tests/test_lifespan.py`, was created to specifically test the lifespan events. The initial approach involved creating a FastAPI app with the lifespan manager and using an `AsyncClient` to trigger the events. However, this approach did not work as the `AsyncClient` does not trigger the lifespan events.

## Manually Triggering Lifespan Events

The next approach involved manually triggering the lifespan events using `app.router.startup()` and `app.router.shutdown()`. This also failed because it did not correctly await the lifespan context manager.

## Using the Lifespan Context Manager Directly

The final and successful approach involved using the `lifespan` context manager directly in the test. This provided the necessary control over the execution of the startup and shutdown events.

### Code

```python
import pytest
from unittest.mock import patch
from fastapi import FastAPI

from app.core.lifespan import build_lifespan
from app.core.config import AppSettings, Environment

@pytest.fixture
def mock_settings():
    """Fixture for AppSettings."""
    return AppSettings(
        environment=Environment.TEST,
        project_version="0.1.0",
        log_level="INFO",
        # Add other necessary settings
    )

@pytest.mark.asyncio
async def test_lifespan_events(mock_settings):
    """
    Test that startup and shutdown events are logged correctly.
    """
    with patch("app.core.lifespan.structlog.get_logger") as mock_get_logger:
        mock_logger = mock_get_logger.return_value
        lifespan = build_lifespan(mock_settings)
        app = FastAPI()

        async with lifespan(app):
            mock_logger.info.assert_called_once_with(
                "application.startup",
                environment="test",
                version="0.1.0",
            )
        
        mock_logger.info.assert_called_with("application.shutdown")
```

This test now successfully patches the logger, creates a lifespan manager, and then asserts that the startup and shutdown events are logged correctly.
