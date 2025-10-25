# Quick Start Guide

Get up and running with FastAPI Production Starter in 5 minutes!

## Prerequisites

- Python 3.11+
- Git
- (Optional) Docker & Docker Compose

## Method 1: Automated Setup (Recommended)

### 1. Clone and Setup

```bash
git clone https://github.com/thesidshah/fastapi-production-starter.git
cd fastapi-production-starter
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- Check Python version
- Create virtual environment
- Install dependencies
- Copy `.env.example` to `.env`
- Run tests
- Generate a sample JWT secret

### 2. Configure Environment

Edit `.env` and update these critical settings:

```bash
# Generate a secure secret
SECURITY_JWT_SECRET=$(openssl rand -hex 32)

# Set your CORS origins
APP_CORS_ALLOW_ORIGINS=["http://localhost:3000"]
```

### 3. Start Development Server

```bash
./scripts/dev.sh
```

Visit:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## Method 2: Manual Setup

### 1. Clone Repository

```bash
git clone https://github.com/thesidshah/fastapi-production-starter.git
cd fastapi-production-starter
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Start Server

```bash
uvicorn app.main:app --factory --reload
```

## Method 3: Docker (Production-like)

### Quick Start with Docker Compose

```bash
# Generate JWT secret
export SECURITY_JWT_SECRET=$(openssl rand -hex 32)

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f app

# Stop services
docker-compose down
```

Services:
- API: http://localhost:8000
- Redis: localhost:6379

### Build Docker Image Only

```bash
docker build -t fastapi-starter .
docker run -p 8000:8000 \
  -e SECURITY_JWT_SECRET=$(openssl rand -hex 32) \
  fastapi-starter
```

## First API Call

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-22T12:00:00.000Z"
}
```

### Get Metadata

```bash
curl http://localhost:8000/api/v1/health/info
```

## Testing Your Setup

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
./scripts/test.sh
```

### Run Linting

```bash
./scripts/lint.sh
```

## Next Steps

### 1. Explore the API

Open http://localhost:8000/docs to see interactive documentation.

### 2. Add Your First Endpoint

Create a new file `src/app/api/routes/example.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/example", tags=["example"])

@router.get("/")
async def get_example():
    return {"message": "Hello from example!"}
```

Register it in `src/app/api/routes/__init__.py`:

```python
from app.api.routes import example

def register_routes(app):
    app.include_router(example.router)
```

### 3. Enable Advanced Features

#### Enable Redis-based Rate Limiting

```bash
# In .env
SECURITY_REDIS_ENABLED=true
SECURITY_REDIS_URL=redis://localhost:6379/0

# Install dependencies
pip install -e ".[phase2]"

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine
```

#### Enable Prometheus Metrics

```bash
# In .env
SECURITY_ENABLE_PROMETHEUS=true

# Install dependencies
pip install -e ".[phase3]"
```

### 4. Read the Documentation

- [README.md](README.md) - Full documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [SECURITY.md](SECURITY.md) - Security best practices
- [Async database integration](docs/integrations/database.md) - End-to-end SQLAlchemy example
- [docs/](docs/) - Additional documentation

## Common Issues

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Python Version Issues

```bash
# Check version
python3 --version

# Use specific version
python3.11 -m venv .venv
```

### Dependencies Not Installing

```bash
# Upgrade pip
pip install --upgrade pip

# Clear cache and reinstall
pip cache purge
pip install -e ".[dev]" --no-cache-dir
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
redis-cli ping
```

## Development Workflow

### 1. Make Changes

Edit files in `src/app/`

### 2. Run Tests

```bash
pytest
```

### 3. Lint Code

```bash
./scripts/lint.sh
```

### 4. Test Manually

Visit http://localhost:8000/docs

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
```

## Production Deployment

### Quick Production Setup

For single-server production deployment:

1. **Set production environment variables** (`.env` or export):
```bash
APP_ENVIRONMENT=production
APP_DEBUG=false
APP_LOG_FORMAT=json
SECURITY_JWT_SECRET=$(openssl rand -hex 32)
SECURITY_ENABLE_HSTS=true
APP_CORS_ALLOW_ORIGINS=["https://yourapp.com"]
```

2. **Install scaling dependencies**:
```bash
pip install -e ".[scaling]"
```

3. **Run with Gunicorn** (Level 2 scaling):
```bash
gunicorn app.main:create_app --factory -c gunicorn.conf.py
```

Or use the included production compose file:
```bash
docker-compose -f deployment/docker-compose.prod.yml up -d
```

### Scaling Your Deployment

The backend includes a **progressive 4-level scaling architecture**. Choose based on your traffic:

**Level 1: Multi-Worker** (10-50K req/sec) - Config only
```bash
# No extra dependencies needed
uvicorn app.main:create_app --factory --workers 4 --port 8000
```

**Level 2: Gunicorn** (50-100K req/sec) - Process management
```bash
# Install scaling dependencies
pip install -e ".[scaling]"

# Run with included config
gunicorn app.main:create_app --factory -c gunicorn.conf.py
```

**Level 3: Background Tasks** - Async work
```bash
# Start RQ workers for long-running tasks
docker-compose up -d worker

# Or manually
rq worker default --url redis://localhost:6379/1
```

**Level 4: Horizontal Scaling** (100K+ req/sec) - Multi-node
```bash
# Kubernetes deployment
pip install -e ".[k8s]"
python -m deployment.plugins.kubernetes deploy --namespace production

# OR Docker Swarm deployment
pip install -e ".[swarm]"
python -m deployment.plugins.swarm deploy --stack-name myapp
```

📖 **Complete Guides**:
- [Scaling Overview](docs/scaling/README.md) - All 4 levels explained
- [Backend Guide: Scaling](docs/BACKEND_GUIDE.md#phase-4-scaling-architecture-) - Detailed architecture
- [Load Testing](docs/scaling/load-testing.md) - Measure performance
- [Troubleshooting](docs/scaling/troubleshooting.md) - Common issues

### Production Checklist

Before deploying to production:

- [ ] Set `APP_ENVIRONMENT=production`
- [ ] Generate and set strong `SECURITY_JWT_SECRET`
- [ ] Configure `APP_CORS_ALLOW_ORIGINS` with actual domains
- [ ] Set `APP_DEBUG=false`
- [ ] Use `APP_LOG_FORMAT=json` for log aggregation
- [ ] Enable HSTS: `SECURITY_ENABLE_HSTS=true`
- [ ] Set up database with proper credentials
- [ ] Configure Redis for sessions/caching (Phase 2+)
- [ ] Set up health check monitoring
- [ ] Configure backup and disaster recovery
- [ ] Review [SECURITY.md](SECURITY.md) recommendations

## Getting Help

- **Documentation**: Check `/docs` directory
- **Issues**: [GitHub Issues](https://github.com/thesidshah/fastapi-production-starter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/thesidshah/fastapi-production-starter/discussions)

## What's Next?

- ⭐ Star the repository
- 📖 Read the full [README.md](README.md)
- 🤝 Check [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
- 🔒 Review [SECURITY.md](SECURITY.md) for security best practices

Happy building! 🚀
