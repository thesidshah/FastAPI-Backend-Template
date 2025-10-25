# Level 1: Multi-Worker Uvicorn

**Complexity**: ⭐ (Configuration only, no code changes)
**Performance**: 10-50K requests/second on 8-core machine
**When to use**: You have a multi-core server and need better CPU utilization

## Overview

Level 1 introduces the simplest form of scaling: running multiple uvicorn worker processes on a single machine. Each worker runs in its own process, handling requests independently. The operating system automatically distributes incoming connections across workers.

This is a **configuration-only change** - no code modifications required. It's the perfect first step when deploying to production and you want to utilize all available CPU cores.

## How It Works

```
┌──────────────────────────────────────────┐
│         Single Machine (8 cores)         │
│                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ Uvicorn  │  │ Uvicorn  │  │ Uvicorn││
│  │ Worker 1 │  │ Worker 2 │  │ Worker3││
│  └──────────┘  └──────────┘  └────────┘│
│       │              │            │     │
│       └──────────────┴────────────┘     │
│              Shared port 8000            │
└──────────────────────────────────────────┘
                    ▲
                    │
            Incoming requests
```

**Key characteristics**:
- Each worker is a separate Python process
- Workers share the same port using SO_REUSEPORT socket option
- OS kernel distributes connections across workers (load balancing at TCP level)
- Workers don't communicate with each other (no shared state)
- Each worker has its own event loop and memory space

## Setup

### Command Line

The simplest way to use multi-worker mode:

```bash
# Production: 4 workers
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers 4

# Auto-detect CPU cores (workers = cores)
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers 0
```

### Environment Variable

Set worker count via environment:

```bash
# .env
WORKERS=4
```

Then start with:
```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers $WORKERS
```

### Docker

Update your Dockerfile CMD:

```dockerfile
# Before (single worker)
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# After (4 workers)
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Or use environment variable
ENV WORKERS=4
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "${WORKERS}"]
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WORKERS=4  # Or use ${WORKERS:-4} for default
    command: >
      uvicorn app.main:create_app --factory
      --host 0.0.0.0
      --port 8000
      --workers 4
```

## Worker Count Recommendations

**Rule of thumb**: `workers = (2 × CPU cores) + 1`

This formula accounts for:
- Some workers waiting on I/O
- One spare worker for handling spikes
- Optimal CPU utilization without oversubscription

**Examples**:

| Server Type | CPU Cores | Recommended Workers | Rationale |
|-------------|-----------|---------------------|-----------|
| t3.medium | 2 | 4 | 2×2+1 = 5, but 4 is safer |
| t3.large | 2 | 4 | Same as above |
| t3.xlarge | 4 | 8-9 | 2×4+1 = 9 |
| t3.2xlarge | 8 | 16-17 | 2×8+1 = 17 |
| Local dev | 4-8 | 1-2 | Keep it simple |

**Considerations**:
- **Memory**: Each worker uses ~50-100MB RAM + your app's memory footprint
- **I/O bound**: More workers = better (can handle more concurrent requests)
- **CPU bound**: More workers doesn't help much (bound by actual CPU cores)
- **Database connections**: Each worker maintains its own connection pool

## Performance Expectations

**Single worker baseline** (8-core machine):
- Simple requests: ~1,000 req/sec
- Database queries: ~500 req/sec
- With authentication: ~300 req/sec

**Multi-worker (4 workers)**:
- Simple requests: ~3,500 req/sec (3.5x improvement)
- Database queries: ~1,800 req/sec (3.6x improvement)
- With authentication: ~1,100 req/sec (3.7x improvement)

**Multi-worker (8 workers)**:
- Simple requests: ~6,500 req/sec (6.5x improvement)
- Database queries: ~3,200 req/sec (6.4x improvement)
- With authentication: ~2,000 req/sec (6.7x improvement)

**Why not perfect linear scaling?**
- Shared resources (database, cache, network)
- Context switching overhead
- Lock contention in Python (GIL for CPU-bound operations)

## Verification

### Check Running Workers

```bash
# See all uvicorn worker processes
ps aux | grep uvicorn

# Output example:
# user  1234  0.0  0.5  uvicorn [master]
# user  1235  2.1  1.2  uvicorn [worker 1]
# user  1236  2.0  1.1  uvicorn [worker 2]
# user  1237  2.1  1.2  uvicorn [worker 3]
# user  1238  2.0  1.1  uvicorn [worker 4]
```

### Test Load Distribution

```bash
# Install siege for load testing
apt-get install siege  # or brew install siege

# Send concurrent requests
siege -c 50 -t 30s http://localhost:8000/api/health

# Check worker distribution in logs
# Each worker should handle roughly equal requests
```

### Monitor Worker CPU Usage

```bash
# Install htop
apt-get install htop  # or brew install htop

# Watch CPU usage across cores
htop

# You should see multiple Python processes at ~100% across different cores
```

## Common Issues

### Issue 1: Workers Not Starting

**Symptoms**: Application starts but only one process visible

**Causes**:
- `--workers` flag missing or set to 1
- Running with `--reload` (incompatible with multi-worker)
- Port already in use

**Solutions**:
```bash
# Verify workers setting
echo $WORKERS  # Should be > 1

# Don't use --reload with --workers
uvicorn app.main:create_app --factory --workers 4  # ✅ Good
uvicorn app.main:create_app --factory --workers 4 --reload  # ❌ Bad (reload disabled)

# Check port availability
lsof -i :8000  # Kill existing processes if needed
```

### Issue 2: Inconsistent Behavior Across Requests

**Symptoms**: Different responses from same endpoint, state not preserved

**Cause**: Each worker has independent memory - in-memory state is not shared

**Solution**: Use external state storage:
```python
# ❌ Bad: In-memory dict (not shared across workers)
app_state = {}

@app.post("/api/data")
async def store_data(data: dict):
    app_state[data["id"]] = data  # Only in THIS worker's memory!

# ✅ Good: Use Redis for shared state
from redis import asyncio as aioredis

@app.post("/api/data")
async def store_data(data: dict, redis: aioredis.Redis = Depends(get_redis)):
    await redis.set(f"data:{data['id']}", json.dumps(data))
```

### Issue 3: Database Connection Pool Exhaustion

**Symptoms**: "Too many connections" errors under load

**Cause**: Each worker creates its own connection pool

**Solution**: Adjust pool size based on worker count:
```python
# config.py
from app.core.config import settings

# Calculate pool size: total connections / workers
workers = settings.workers or 1
pool_size = max(5, 20 // workers)  # At least 5, max 20 total

DATABASE_URL = (
    f"postgresql+asyncpg://...?"
    f"pool_size={pool_size}&"
    f"max_overflow=10"
)
```

### Issue 4: High Memory Usage

**Symptoms**: Server running out of memory with multiple workers

**Cause**: Each worker duplicates application memory

**Solution**:
```bash
# Monitor memory per worker
ps aux | grep uvicorn | awk '{print $6/1024 " MB"}'

# Reduce workers if memory-constrained
# Better: Upgrade server or optimize application memory usage
```

## Limitations

Level 1 is simple but has limitations:

1. **No health monitoring** - Workers can fail silently
2. **No graceful restarts** - Deploying new code requires downtime
3. **No auto-restart** - Crashed workers stay dead
4. **Manual process management** - You must track and manage worker processes yourself
5. **Limited observability** - Hard to see which worker handled which request

**When to upgrade to Level 2:**
- You need zero-downtime deployments
- Workers are crashing and need auto-restart
- You want better visibility into worker health
- You need graceful shutdown handling

## Best Practices

### 1. Start Conservative

```bash
# Begin with 2-4 workers, monitor, then scale up
WORKERS=4  # Start here
```

### 2. Monitor Resource Usage

```bash
# Watch CPU and memory before adding more workers
htop
# Target: 70-80% CPU utilization across all cores
```

### 3. Configure Connection Pools

```python
# Adjust database pool size based on worker count
pool_size_per_worker = 5
total_workers = 4
max_db_connections = pool_size_per_worker * total_workers  # = 20
```

### 4. Use Stateless Design

```python
# ❌ Bad: Worker-local state
request_cache = {}

# ✅ Good: External state
from redis import asyncio as aioredis
redis_client = aioredis.from_url("redis://localhost")
```

### 5. Test with Load

```bash
# Verify scaling with real load
siege -c 100 -t 60s http://localhost:8000/api/endpoint

# Compare single worker vs multi-worker
# Expect: ~(workers - 1)x improvement
```

## Example Deployment

### Dockerfile (Level 1)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

# Copy application
COPY src/ ./src/

# Set environment
ENV PYTHONPATH=/app/src
ENV WORKERS=4

# Expose port
EXPOSE 8000

# Run with multiple workers
CMD ["uvicorn", "app.main:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "${WORKERS}"]
```

### Docker Compose (Level 1)

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WORKERS=4
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

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

## Next Steps

Once Level 1 is working:

1. **Monitor performance** - Use [load-testing.md](load-testing.md) to establish baselines
2. **Tune worker count** - Experiment with different worker counts
3. **Identify limitations** - Watch for crashes, restarts, deploy issues
4. **Consider Level 2** - When you need production-grade reliability

Ready for production-grade process management? See [Level 2: Gunicorn Process Manager](level2-gunicorn.md).

## References

- [Uvicorn Deployment Guide](https://www.uvicorn.org/deployment/)
- [FastAPI Deployment with Workers](https://fastapi.tiangolo.com/deployment/server-workers/)
- [SO_REUSEPORT Explanation](https://lwn.net/Articles/542629/)
