
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
