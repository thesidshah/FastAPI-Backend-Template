# FastAPI Production Starter Template

A production-ready FastAPI starter kit following modern Python best practices. Built with security, observability, and developer experience in mind.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

### Core Capabilities
- **FastAPI app factory** with environment-aware settings and lifespan hooks
- **Structured logging** via `structlog` with request correlation IDs
- **Extensible routing layer** with dependency injection templates
- **Centralized configuration** using `pydantic-settings` and `.env`
- **Health & readiness checks** with baseline metadata endpoints
- **Comprehensive testing** with pytest + httpx async client

### Security & Monitoring
- **Rate limiting** with sliding window algorithm
- **JWT authentication** with token refresh support
- **Request ID tracking** for distributed tracing
- **Prometheus metrics** integration ready
- **GeoIP blocking** capabilities
- **Security headers** and CORS configuration

### Developer Experience
- **Type-safe** configuration and schemas
- **Async-first** architecture
- **Linting & formatting** with Ruff, Black, and MyPy
- **Pre-configured** testing suite with coverage
- **Modular architecture** for easy extensibility

## Quick Start

### Prerequisites
- Python 3.11 or higher
- pip or uv package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/thesidshah/FastAPI-Backend-Template
cd FastAPI-Backend-Template
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
# Using pip
pip install -e ".[dev]"

# Or using uv (faster)
uv pip install -e ".[dev]"
```

4. Copy environment configuration:
```bash
cp .env.example .env
```

5. Run the development server:
```bash
uvicorn app.main:app --factory --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/docs` for interactive API documentation.

## Project Structure

```
.
├── src/
│   └── app/
│       ├── api/              # API routes and endpoints
│       │   └── routes/       # Feature-specific routers
│       ├── core/             # Core application configuration
│       │   ├── config.py     # Settings management
│       │   ├── logging.py    # Structured logging setup
│       │   ├── middleware.py # Middleware registration
│       │   └── lifespan.py   # Startup/shutdown hooks
│       ├── middleware/       # Custom middleware
│       │   ├── auth.py       # JWT authentication
│       │   ├── rate_limit.py # Rate limiting
│       │   ├── security.py   # Security headers
│       │   └── monitoring.py # Request logging & metrics
│       ├── dependencies/     # FastAPI dependency providers
│       ├── schemas/          # Pydantic models
│       ├── services/         # Business logic layer
│       ├── integrations/     # External service integrations
│       └── utils/            # Utility functions
├── tests/                    # Test suite
├── docs/                     # Documentation
├── pyproject.toml           # Project metadata & dependencies
└── .env.example             # Environment configuration template
```

## Configuration

Settings are managed via `src/app/core/config.py` using Pydantic settings. All configuration can be set via environment variables prefixed with `APP_`.

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENVIRONMENT` | Environment (`local`, `staging`, `production`, `test`) | `local` |
| `APP_LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `APP_LOG_FORMAT` | Log format (`json` or `console`) | `json` |
| `APP_API_PREFIX` | API route prefix | `/api/v1` |

### Security Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_CORS_ALLOW_ORIGINS` | Allowed CORS origins (JSON array) | `[]` |
| `APP_ALLOWED_HOSTS` | Trusted host headers (JSON array) | `["*"]` |
| `APP_JWT_SECRET_KEY` | Secret key for JWT signing | Required in production |
| `APP_JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` |

### Rate Limiting

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `APP_RATE_LIMIT_REQUESTS` | Requests per window | `100` |
| `APP_RATE_LIMIT_WINDOW_SECONDS` | Time window in seconds | `60` |

See `.env.example` for a complete list of configuration options.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_health.py
```

### Linting & Formatting

```bash
# Check code with Ruff
ruff check src tests

# Format code with Black
black src tests

# Type checking with MyPy
mypy src
```

### Adding New Features

1. **Create a new router** in `src/app/api/routes/<feature>.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/feature", tags=["feature"])

@router.get("/")
async def get_feature():
    return {"message": "Feature endpoint"}
```

2. **Register the router** in `src/app/api/routes/__init__.py`:
```python
from app.api.routes import feature

def register_routes(app):
    app.include_router(feature.router)
```

3. **Add business logic** in `src/app/services/<feature>.py`

4. **Create Pydantic schemas** in `src/app/schemas/<feature>.py`

5. **Write tests** in `tests/test_<feature>.py`

## Security Features

### JWT Authentication

Protected routes require a valid JWT token:

```python
from app.middleware.auth import get_current_user

@router.get("/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    return {"user": user}
```

### Rate Limiting

Rate limiting is automatically applied to all routes. Configure via environment variables or customize per-route:

```python
from app.middleware.rate_limit import rate_limit

@router.get("/limited", dependencies=[Depends(rate_limit(requests=10, window=60))])
async def limited_route():
    return {"message": "Rate limited endpoint"}
```

### Security Headers

Automatically applied security headers include:
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Strict-Transport-Security
- Content-Security-Policy

## Logging & Observability

### Structured Logging

All logs are structured using `structlog` with automatic request ID correlation:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("user_action", user_id=user.id, action="login")
```

### Request Tracing

Every request receives a unique `X-Request-ID` header for distributed tracing. Enable request body logging in development:

```bash
APP_DEBUG=true
```

### Health Checks

- **Liveness**: `GET /api/v1/health` - Basic health check
- **Readiness**: `GET /api/v1/health/ready` - Checks downstream dependencies
- **Metadata**: `GET /api/v1/health/info` - Application metadata

## Deployment

### Production Checklist

- [ ] Set `APP_ENVIRONMENT=production`
- [ ] Configure `APP_JWT_SECRET_KEY` with a strong secret
- [ ] Set appropriate `APP_CORS_ALLOW_ORIGINS`
- [ ] Configure `APP_ALLOWED_HOSTS`
- [ ] Set `APP_LOG_FORMAT=json` for log aggregation
- [ ] Disable debug mode: `APP_DEBUG=false`
- [ ] Configure external dependencies (Redis, databases, etc.)

### Running with Gunicorn

```bash
gunicorn app.main:app --factory \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker Deployment

Example Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install .

COPY src/ ./src/

CMD ["uvicorn", "app.main:app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

## Advanced Features

### Phase 2: Redis & Caching

Install phase 2 dependencies:
```bash
pip install -e ".[phase2]"
```

Configure Redis for session storage and caching.

### Phase 3: Metrics & GeoIP

Install phase 3 dependencies:
```bash
pip install -e ".[phase3]"
```

Enables Prometheus metrics and GeoIP blocking capabilities.

### All Security Features

Install all security features:
```bash
pip install -e ".[security]"
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Pydantic](https://pydantic.dev/) - Data validation
- [Structlog](https://www.structlog.org/) - Structured logging
- [Uvicorn](https://www.uvicorn.org/) - ASGI server

## Support

- **Documentation**: Check the `/docs` directory
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join GitHub Discussions for questions

---

Made with ❤️ for the Python community by @thesidshah
