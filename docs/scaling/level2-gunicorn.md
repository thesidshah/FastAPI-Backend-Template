# Level 2: Gunicorn Process Manager

**Complexity**: ⭐⭐ (Add gunicorn.conf.py, update Dockerfile)
**Performance**: 50-100K requests/second with proper tuning
**When to use**: You need production-grade reliability and zero-downtime deployments

## Overview

Level 2 introduces **Gunicorn** (Green Unicorn), a battle-tested WSGI/ASGI server that manages uvicorn workers with production-grade features. While Level 1 runs multiple workers, they're independent processes with no supervision. Gunicorn adds a master process that monitors workers, handles graceful restarts, and enables zero-downtime deployments.

Think of Gunicorn as a "process supervisor" - it watches your workers, restarts them when they crash, recycles them to prevent memory leaks, and coordinates graceful shutdowns.

## Why Gunicorn Over Level 1?

### What Gunicorn Adds

| Feature | Level 1 (Uvicorn) | Level 2 (Gunicorn) |
|---------|-------------------|-------------------|
| **Worker management** | Manual | Automatic |
| **Health monitoring** | None | Built-in |
| **Auto-restart on crash** | No | Yes |
| **Graceful shutdown** | Basic | Advanced |
| **Zero-downtime reload** | No | Yes (SIGHUP) |
| **Worker recycling** | No | Yes (prevents memory leaks) |
| **Timeout handling** | Limited | Configurable per worker |
| **Signal handling** | Basic | Full control (HUP, TERM, INT, etc.) |
| **Logging** | Basic | Production-grade |

### Real-World Scenarios

**Scenario 1: Worker crashes**
- **Level 1**: Worker stays dead, capacity reduced
- **Level 2**: Master detects crash, spawns replacement worker automatically

**Scenario 2: Deploying new code**
- **Level 1**: Stop all workers → downtime → start new workers
- **Level 2**: Send SIGHUP → workers gracefully finish requests → restart with new code (zero downtime)

**Scenario 3: Memory leak in worker**
- **Level 1**: Worker memory grows indefinitely until OOM
- **Level 2**: After handling max_requests, worker gracefully exits and is replaced

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                   Gunicorn Master Process                  │
│  • Spawns and monitors workers                            │
│  • Handles signals (HUP, TERM, INT, QUIT)                 │
│  • Restarts crashed workers                               │
│  • Coordinates graceful shutdowns                         │
└────────────┬───────────────────────────────────┬──────────┘
             │                                   │
    ┌────────▼────────┐               ┌────────▼────────┐
    │ Uvicorn Worker 1│               │ Uvicorn Worker 2│
    │  • PID: 1235    │               │  • PID: 1236    │
    │  • Requests: 894│               │  • Requests: 901│
    │  • Uptime: 45m  │               │  • Uptime: 45m  │
    └─────────────────┘               └─────────────────┘

    ┌─────────────────┐               ┌─────────────────┐
    │ Uvicorn Worker 3│      ...      │ Uvicorn Worker N│
    │  • PID: 1237    │               │  • PID: 1238    │
    │  • Requests: 887│               │  • Requests: 895│
    │  • Uptime: 45m  │               │  • Uptime: 45m  │
    └─────────────────┘               └─────────────────┘
```

## Setup

### 1. Install Gunicorn

Add to your project dependencies:

```bash
# Using uv
uv add gunicorn

# Or pip
pip install gunicorn
```

Already included in `pyproject.toml`:
```toml
[project.dependencies]
gunicorn = ">=23.0.0"
```

### 2. Create Gunicorn Configuration

Create `gunicorn.conf.py` in your project root:

```python
"""
Gunicorn configuration for production deployment.

This file configures the Gunicorn ASGI server for running FastAPI
with multiple worker processes, health monitoring, and graceful restarts.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048  # Max queued connections

# Worker processes
workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000  # Max simultaneous connections per worker
max_requests = int(os.getenv("MAX_REQUESTS", "1000"))  # Restart worker after N requests
max_requests_jitter = int(os.getenv("MAX_REQUESTS_JITTER", "100"))  # Add randomness to prevent thundering herd

# Timeouts
timeout = int(os.getenv("WORKER_TIMEOUT", "30"))  # Worker silence timeout (seconds)
graceful_timeout = int(os.getenv("GRACEFUL_TIMEOUT", "30"))  # Grace period for shutdown
keepalive = int(os.getenv("KEEPALIVE", "5"))  # Keep-alive timeout

# Server mechanics
preload_app = False  # Don't preload app (allows code reload)
daemon = False  # Don't daemonize (Docker handles this)
pidfile = None  # No PID file needed (Docker handles this)
user = None  # Run as current user (Docker sets this)
group = None

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "production-fastapi-backend"

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Gunicorn master starting")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading workers")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"Gunicorn ready. Workers: {workers}, Bind: {bind}")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received INT/QUIT signal")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.warning(f"Worker {worker.pid} aborted (timeout or crash)")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")

def worker_exit(server, worker):
    """Called just after a worker has been exited, in the master process."""
    server.log.info(f"Worker {worker.pid} exited")
```

### 3. Update Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY gunicorn.conf.py ./

# Set environment
ENV PYTHONPATH=/app/src
ENV WORKERS=4

# Expose port
EXPOSE 8000

# Run with Gunicorn (replaces direct uvicorn call)
CMD ["gunicorn", "app.main:create_app()", \
     "--config", "gunicorn.conf.py"]
```

Note the command change:
- **Before (Level 1)**: `uvicorn app.main:create_app --factory --workers 4`
- **After (Level 2)**: `gunicorn app.main:create_app() --config gunicorn.conf.py`

**Important**: Gunicorn doesn't support the `--factory` pattern directly. Instead:
- Change `app.main:create_app` → `app.main:create_app()`
- Or use factory wrapper (see below)

### 4. Factory Pattern Support

If you need true factory pattern (e.g., different configs per worker), create a wrapper:

```python
# src/app/gunicorn_app.py
"""Gunicorn application factory wrapper."""

from app.main import create_app

# Create application instance for Gunicorn
app = create_app()
```

Then in Dockerfile:
```dockerfile
CMD ["gunicorn", "app.gunicorn_app:app", \
     "--config", "gunicorn.conf.py"]
```

### 5. Environment Variables

Configure via `.env`:

```bash
# Worker configuration
WORKERS=4                    # Number of worker processes (default: CPU*2+1)
WORKER_TIMEOUT=30            # Worker timeout in seconds
GRACEFUL_TIMEOUT=30          # Graceful shutdown timeout
MAX_REQUESTS=1000            # Restart worker after N requests (prevents memory leaks)
MAX_REQUESTS_JITTER=100      # Add randomness to max_requests

# Logging
LOG_LEVEL=info               # debug, info, warning, error, critical

# Server
PORT=8000
KEEPALIVE=5                  # Keep-alive timeout
```

## Running Gunicorn

### Command Line

```bash
# Basic usage
gunicorn app.main:create_app() --config gunicorn.conf.py

# With custom config file
gunicorn app.main:create_app() --config /path/to/gunicorn.conf.py

# Override workers
gunicorn app.main:create_app() --config gunicorn.conf.py --workers 8

# With specific bind address
gunicorn app.main:create_app() --config gunicorn.conf.py --bind 0.0.0.0:8080
```

### Docker Compose

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WORKERS=4
      - WORKER_TIMEOUT=30
      - MAX_REQUESTS=1000
      - LOG_LEVEL=info
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    command: gunicorn app.main:create_app() --config gunicorn.conf.py

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Zero-Downtime Deployment

One of Gunicorn's killer features: **deploy new code without dropping requests**.

### How It Works

1. **Build new Docker image** with updated code
2. **Send SIGHUP signal** to Gunicorn master process
3. **Master process** coordinates graceful reload:
   - Spawn new workers with new code
   - Old workers finish in-flight requests
   - Old workers shut down when idle
   - New workers take over traffic

### Deployment Process

```bash
# Option 1: Docker container (send HUP to container)
docker kill --signal=HUP production-fastapi-backend

# Option 2: Docker Compose
docker-compose kill -s HUP web

# Option 3: Direct process (find master PID)
pkill -HUP gunicorn

# Option 4: Kubernetes (rolling update handles this)
kubectl rollout restart deployment/production-fastapi-backend
```

### Zero-Downtime Verification

```bash
# Start load test before deployment
siege -c 50 -t 300s http://localhost:8000/api/health &

# Deploy new code (in another terminal)
docker-compose build web
docker-compose kill -s HUP web

# Check siege results (should show 100% availability)
# No dropped requests during reload!
```

## Worker Management

### Signal Handling

Gunicorn responds to Unix signals for process management:

| Signal | Action | Use Case |
|--------|--------|----------|
| **HUP** | Graceful reload | Deploy new code (zero downtime) |
| **TERM** | Graceful shutdown | Stop server gracefully |
| **INT** | Quick shutdown | Emergency stop (Ctrl+C) |
| **QUIT** | Graceful shutdown (workers first) | Clean stop |
| **USR1** | Reopen log files | Log rotation |
| **USR2** | Upgrade Gunicorn binary | Hot upgrade |
| **TTIN** | Increase worker count (+1) | Scale up |
| **TTOU** | Decrease worker count (-1) | Scale down |

### Dynamic Scaling

Scale workers without restart:

```bash
# Add one worker
kill -TTIN <gunicorn-master-pid>

# Remove one worker
kill -TTOU <gunicorn-master-pid>

# Find master PID
ps aux | grep gunicorn | grep master
```

### Worker Recycling

Workers automatically restart after handling `max_requests` to prevent memory leaks:

```python
# gunicorn.conf.py
max_requests = 1000  # Restart after 1000 requests
max_requests_jitter = 100  # Add randomness (900-1100)
```

This prevents:
- Gradual memory growth from small leaks
- All workers restarting simultaneously (jitter spreads it out)
- Long-running workers with accumulated bugs

## Health Monitoring

### Worker Health Checks

Gunicorn monitors workers via timeout:

```python
# gunicorn.conf.py
timeout = 30  # Worker must show activity within 30 seconds
```

If a worker is silent for 30 seconds:
1. Master sends SIGABRT to worker
2. Worker terminates
3. Master spawns replacement worker

### Application Health Endpoint

Enhance your health check for load balancer integration:

```python
# src/app/api/routes/health.py
import os
import time
from fastapi import APIRouter

router = APIRouter()

# Track worker start time
WORKER_START_TIME = time.time()

@router.get("/health")
async def health():
    """Basic health check."""
    return {"status": "healthy"}

@router.get("/health/worker")
async def worker_health():
    """Worker-specific health check for load balancer."""
    return {
        "status": "healthy",
        "worker_id": os.getpid(),
        "uptime_seconds": time.time() - WORKER_START_TIME,
    }

@router.get("/health/ready")
async def readiness():
    """Readiness probe (check dependencies)."""
    # Check database
    # Check Redis
    # Check external services
    return {"status": "ready"}
```

## Performance Tuning

### Worker Count

**General formula**: `workers = (2 × CPU cores) + 1`

```python
# gunicorn.conf.py
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
```

**Adjust based on workload**:
- **I/O-bound** (API calls, DB queries): More workers = better (2-4x CPU cores)
- **CPU-bound** (image processing, calculations): Fewer workers (1x CPU cores)
- **Memory-constrained**: Fewer workers (monitor RAM usage)

### Worker Connections

```python
# gunicorn.conf.py
worker_connections = 1000  # Max simultaneous connections per worker
```

**Calculation**:
- Each connection uses ~1-2MB RAM
- `Total memory = workers × worker_connections × 1.5MB`
- Example: 4 workers × 1000 connections × 1.5MB = 6GB RAM

### Timeouts

```python
# gunicorn.conf.py
timeout = 30              # Worker must respond within 30s
graceful_timeout = 30     # Allow 30s for graceful shutdown
keepalive = 5             # Keep-alive for 5s
```

**Guidelines**:
- **timeout**: Set to 95th percentile response time + buffer
- **graceful_timeout**: Allow time for longest request to complete
- **keepalive**: Balance between connection reuse and resource consumption

### Worker Recycling

```python
# gunicorn.conf.py
max_requests = 1000           # Restart after 1000 requests
max_requests_jitter = 100     # Add randomness (900-1100)
```

**Benefits**:
- Prevents memory leaks from accumulating
- Clears any stale state
- Distributes restarts over time (jitter prevents thundering herd)

## Troubleshooting

### Issue 1: Workers Timing Out

**Symptoms**: Workers frequently restarted with "Worker timeout" errors

**Causes**:
- Slow database queries
- External API calls taking too long
- Blocking I/O in async context

**Solutions**:
```python
# Increase timeout for slow operations
timeout = 60  # Instead of 30

# Or fix slow operations:
# - Add database indexes
# - Use async HTTP clients
# - Offload to background tasks (Level 3)
```

### Issue 2: Workers Not Restarting

**Symptoms**: Zero-downtime reload doesn't work

**Causes**:
- `preload_app = True` (prevents reload)
- Wrong signal sent (TERM instead of HUP)
- Master process not receiving signal

**Solutions**:
```python
# gunicorn.conf.py
preload_app = False  # Allow reload

# Send correct signal
docker kill --signal=HUP <container>

# Verify master PID
docker exec <container> ps aux | grep gunicorn
```

### Issue 3: High Memory Usage

**Symptoms**: Workers consuming excessive memory

**Causes**:
- Memory leaks in application code
- Too many workers for available RAM
- Workers not recycling

**Solutions**:
```python
# Enable worker recycling
max_requests = 500  # Recycle more frequently

# Reduce workers
workers = 2  # Instead of 4

# Or identify and fix leaks
```

### Issue 4: Uneven Load Distribution

**Symptoms**: Some workers handle many more requests than others

**Causes**:
- Long-running requests blocking workers
- Incorrect load balancer configuration

**Solutions**:
```python
# Offload long tasks to background queue (Level 3)
# Or increase worker count
workers = 8  # More workers = better distribution
```

## Best Practices

### 1. Use Worker Recycling

```python
max_requests = 1000
max_requests_jitter = 100
```

Prevents memory leaks from accumulating over time.

### 2. Configure Appropriate Timeouts

```python
timeout = 30  # Match 95th percentile response time
graceful_timeout = 30  # Allow longest request to complete
```

### 3. Monitor Worker Health

```bash
# Watch worker restarts
docker logs -f production-fastapi-backend | grep "Worker"

# Count workers
docker exec production-fastapi-backend ps aux | grep uvicorn | wc -l
```

### 4. Use Graceful Shutdown

```bash
# Good: Graceful
docker stop production-fastapi-backend  # Sends TERM, waits graceful_timeout

# Bad: Forceful
docker kill production-fastapi-backend  # Kills immediately
```

### 5. Test Zero-Downtime Deploys

```bash
# Run load test during deployment
siege -c 50 -t 60s http://localhost:8000/api/health &

# Deploy
docker-compose kill -s HUP web

# Verify 100% availability
```

## When to Move to Level 3

Consider Level 3 (Background Tasks) when:
- Requests timeout due to long-running operations
- You need to process uploads, generate reports, send emails
- CPU-intensive operations block request handling
- You want to defer work to off-peak hours

## Next Steps

1. **Deploy with Gunicorn** - Replace uvicorn command with gunicorn
2. **Configure worker count** - Tune based on your server specs
3. **Test zero-downtime reload** - Verify HUP signal works
4. **Monitor worker health** - Watch for timeouts and restarts
5. **Benchmark performance** - Compare to Level 1 baseline

Ready to offload long-running tasks? See [Level 3: Background Task Processing](level3-background-tasks.md).

## References

- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
- [FastAPI Deployment with Gunicorn](https://fastapi.tiangolo.com/deployment/server-workers/)
- [Zero-Downtime Deployments](https://medium.com/@genchilu/graceful-shutdown-and-zero-downtime-deployment-guide-922d3f7ffc1d)
