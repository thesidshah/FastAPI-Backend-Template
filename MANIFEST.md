# Project Manifest

This document provides a complete overview of the FastAPI Production Starter package structure and contents.

## Package Information

- **Name**: fastapi-production-starter
- **Version**: 1.0.0
- **License**: MIT
- **Python**: 3.11+
- **Framework**: FastAPI 0.111+

## Directory Structure

```
fastapi-production-starter/
├── .github/                      # GitHub configuration
│   ├── workflows/
│   │   └── ci.yml               # CI/CD pipeline
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md        # Bug report template
│   │   └── feature_request.md   # Feature request template
│   └── PULL_REQUEST_TEMPLATE.md # PR template
│
├── docs/                        # Documentation
│   ├── core/                    # Core documentation
│   │   ├── middleware.md        # Middleware docs
│   │   └── security.md          # Security docs
│   ├── integrations/            # Integration docs
│   │   └── alerting.md          # Alerting system docs
│   ├── SECURITY_IMPLEMENTATION.md
│   ├── SECURITY_TEMPLATE_COMPLETE.md
│   ├── lifespan_tests.md
│   ├── logging_decorator.md
│   └── reading-the-code.md
│
├── scripts/                     # Utility scripts
│   ├── setup.sh                 # Automated setup
│   ├── dev.sh                   # Development server
│   ├── test.sh                  # Test runner
│   └── lint.sh                  # Code quality checks
│
├── src/                         # Source code
│   └── app/
│       ├── __init__.py
│       ├── main.py              # Application factory
│       │
│       ├── api/                 # API layer
│       │   └── routes/          # Route handlers
│       │
│       ├── core/                # Core functionality
│       │   ├── config.py        # Configuration
│       │   ├── logging.py       # Logging setup
│       │   ├── middleware.py    # Middleware registration
│       │   ├── lifespan.py      # Startup/shutdown
│       │   └── decorators.py    # Utility decorators
│       │
│       ├── middleware/          # Custom middleware
│       │   ├── __init__.py
│       │   ├── auth.py          # JWT authentication
│       │   ├── rate_limit.py    # Rate limiting
│       │   ├── security.py      # Security headers
│       │   ├── monitoring.py    # Request logging
│       │   └── advanced.py      # Advanced features
│       │
│       ├── dependencies/        # FastAPI dependencies
│       │   ├── __init__.py
│       │   ├── config.py        # Config dependencies
│       │   └── services.py      # Service dependencies
│       │
│       ├── schemas/             # Pydantic models
│       │   ├── __init__.py
│       │   └── health.py        # Health check schemas
│       │
│       ├── services/            # Business logic
│       │   └── health.py        # Health check service
│       │
│       ├── integrations/        # External integrations
│       │   └── alerting.py      # Alerting integration
│       │
│       └── utils/               # Utilities
│           └── __init__.py
│
├── tests/                       # Test suite
│   ├── conftest.py              # Test configuration
│   ├── test_health.py           # Health endpoint tests
│   ├── test_lifespan.py         # Lifespan tests
│   ├── test_security_middleware.py
│   └── integrations/            # Integration tests
│
├── .dockerignore                # Docker ignore rules
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── CHANGELOG.md                 # Version history
├── CONTRIBUTING.md              # Contribution guide
├── Dockerfile                   # Docker build file
├── LICENSE                      # MIT License
├── MANIFEST.md                  # This file
├── QUICKSTART.md                # Quick start guide
├── README.md                    # Main documentation
├── SECURITY.md                  # Security policy
├── docker-compose.yml           # Docker Compose config
└── pyproject.toml               # Project metadata
```

## Core Components

### Application Layer

| Component | Location | Purpose |
|-----------|----------|---------|
| App Factory | `src/app/main.py` | Creates FastAPI application instance |
| Configuration | `src/app/core/config.py` | Centralized settings management |
| Logging | `src/app/core/logging.py` | Structured logging setup |
| Lifespan | `src/app/core/lifespan.py` | Startup/shutdown hooks |

### Middleware

| Middleware | Location | Purpose |
|------------|----------|---------|
| Authentication | `src/app/middleware/auth.py` | JWT authentication |
| Rate Limiting | `src/app/middleware/rate_limit.py` | Request rate limiting |
| Security Headers | `src/app/middleware/security.py` | HTTP security headers |
| Request Logging | `src/app/middleware/monitoring.py` | Request/response logging |
| Advanced | `src/app/middleware/advanced.py` | GeoIP, circuit breaker |

### Services

| Service | Location | Purpose |
|---------|----------|---------|
| Health | `src/app/services/health.py` | Health check logic |
| Alerting | `src/app/integrations/alerting.py` | Security alerting |

## Feature Matrix

### Core Features (Always Available)

- ✅ FastAPI application factory
- ✅ Structured logging with correlation IDs
- ✅ Environment-based configuration
- ✅ Health check endpoints
- ✅ In-memory rate limiting
- ✅ Security headers
- ✅ CORS configuration
- ✅ Request validation
- ✅ Async testing suite

### Phase 2 Features (Optional: `pip install -e ".[phase2]"`)

- ✅ JWT authentication
- ✅ Token refresh mechanism
- ✅ Redis-based rate limiting
- ✅ Session management
- ✅ API key authentication

### Phase 3 Features (Optional: `pip install -e ".[phase3]"`)

- ✅ GeoIP blocking
- ✅ Prometheus metrics
- ✅ Circuit breaker pattern
- ✅ DDoS protection
- ✅ Security alerting

## Dependencies

### Core Dependencies
- `fastapi>=0.111,<0.112`
- `uvicorn[standard]>=0.30,<0.31`
- `pydantic-settings>=2.3,<3.0`
- `structlog>=24.2,<25.0`
- `orjson>=3.10,<4.0`
- `python-dotenv>=1.0,<2.0`

### Development Dependencies
- `pytest>=8.2,<9.0`
- `pytest-asyncio>=0.23,<0.24`
- `pytest-cov>=5.0,<6.0`
- `httpx>=0.27,<0.28`
- `ruff>=0.4,<0.5`
- `black>=24.4,<25.0`
- `mypy>=1.10,<2.0`

### Optional Dependencies
- Phase 2: Redis, JWT, Cryptography
- Phase 3: GeoIP2, Prometheus

## Configuration Files

### Python Configuration
- `pyproject.toml` - Project metadata, dependencies, tool configuration

### Docker Configuration
- `Dockerfile` - Multi-stage Docker build
- `docker-compose.yml` - Service orchestration
- `.dockerignore` - Docker build exclusions

### Development Tools
- `.gitignore` - Git exclusions
- `.env.example` - Environment variable template

### CI/CD
- `.github/workflows/ci.yml` - GitHub Actions workflow

## Testing

### Test Coverage
- API endpoints (health, metadata)
- Middleware (auth, rate limiting, security)
- Lifespan hooks
- Integration tests

### Test Commands
```bash
pytest                    # Run all tests
pytest --cov=app         # With coverage
./scripts/test.sh        # Full test suite
```

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup.sh` | Initial setup | `./scripts/setup.sh` |
| `dev.sh` | Development server | `./scripts/dev.sh` |
| `test.sh` | Run tests | `./scripts/test.sh` |
| `lint.sh` | Code quality | `./scripts/lint.sh` |

## Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Main documentation |
| `QUICKSTART.md` | Quick start guide |
| `CONTRIBUTING.md` | Contribution guidelines |
| `SECURITY.md` | Security policy |
| `CHANGELOG.md` | Version history |
| `MANIFEST.md` | This file |

## API Endpoints

### Health Endpoints
- `GET /api/v1/health` - Liveness check
- `GET /api/v1/health/ready` - Readiness check
- `GET /api/v1/health/info` - Application metadata

### Documentation
- `GET /docs` - Swagger UI (dev/staging)
- `GET /redoc` - ReDoc (dev/staging)
- `GET /openapi.json` - OpenAPI schema

## Security Features

### Built-in Security
- Request ID tracking
- Rate limiting (in-memory/Redis)
- Security headers (HSTS, CSP, etc.)
- CORS configuration
- Content validation
- Size limits

### Optional Security
- JWT authentication
- API key authentication
- GeoIP blocking
- Circuit breaker
- DDoS protection
- Security alerting

## Deployment Options

### Development
```bash
uvicorn app.main:app --factory --reload
```

### Production (Uvicorn)
```bash
uvicorn app.main:app --factory --host 0.0.0.0 --port 8000
```

### Production (Gunicorn)
```bash
gunicorn app.main:app --factory \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

### Docker
```bash
docker-compose up -d
```

## Environment Variables

See `.env.example` for complete list. Key variables:

### Required
- `APP_ENVIRONMENT` - Environment name
- `SECURITY_JWT_SECRET` - JWT secret (production)

### Recommended
- `APP_CORS_ALLOW_ORIGINS` - CORS origins
- `APP_LOG_LEVEL` - Logging level
- `SECURITY_RATE_LIMIT_ENABLED` - Enable rate limiting

## License

MIT License - See [LICENSE](LICENSE) file

## Version Information

- **Initial Release**: v1.0.0 (2025-10-22)
- **Python Support**: 3.11+
- **FastAPI Version**: 0.111+

## Maintenance

### Code Quality
- Black (formatting)
- Ruff (linting)
- MyPy (type checking)
- pytest (testing)

### CI/CD
- GitHub Actions
- Automated testing
- Security scanning
- Docker builds

---

Last Updated: 2025-10-22
