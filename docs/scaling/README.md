# Scaling Architecture

The production-fastapi-backend implements a **progressive 4-level scaling architecture** that grows with your needs. Start with a single worker for development, scale to multiple workers for production, add background task processing when needed, and expand to multi-node deployments when traffic demands it.

## Philosophy

**Start minimal, grow as needed.** Each level builds on the previous one without breaking changes. You can adopt higher levels incrementally as your traffic grows:

- **Level 1**: Single machine, multiple processes (10-50K req/sec)
- **Level 2**: Production process management (50-100K req/sec)
- **Level 3**: Background task processing (offload CPU-intensive work)
- **Level 4**: Multi-node horizontal scaling (100K+ req/sec)

## Quick Start

### Development (Single Worker)
```bash
# Default - single uvicorn worker
uvicorn app.main:create_app --factory --reload
```

### Production (Multi-Worker)
```bash
# Level 1 - Multiple uvicorn workers
uvicorn app.main:create_app --factory --workers 4

# Level 2 - Gunicorn with worker management
gunicorn app.main:create_app --factory --config gunicorn.conf.py

# Level 3 - With background tasks
docker-compose up  # Includes RQ worker

# Level 4 - Kubernetes plugin
pip install -e ".[k8s]"
python -m deployment.plugins.kubernetes deploy
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Level 4: Horizontal Scaling                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Load Balancer│───▶│   Node 1     │    │   Node 2     │     │
│  │  (nginx/     │    │              │    │              │     │
│  │   Traefik)   │    └──────────────┘    └──────────────┘     │
│  └──────────────┘           │                     │            │
└────────────────────────────┼─────────────────────┼─────────────┘
                              │                     │
┌─────────────────────────────┼─────────────────────┼─────────────┐
│              Level 3: Background Task Processing   │             │
│         ┌─────────────────┐      ┌─────────────────────────┐   │
│         │  Task Queue     │◀────▶│  RQ Workers             │   │
│         │  (Redis)        │      │  (Separate Processes)   │   │
│         └─────────────────┘      └─────────────────────────┘   │
└────────────────────────────┬─────────────────────┬─────────────┘
                              │                     │
┌─────────────────────────────┼─────────────────────┼─────────────┐
│         Level 2: Gunicorn Process Manager         │             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Gunicorn Master Process                    │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │    │
│  │  │ Uvicorn  │  │ Uvicorn  │  │ Uvicorn  │  ...       │    │
│  │  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │            │    │
│  │  └──────────┘  └──────────┘  └──────────┘            │    │
│  └────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼─────────────────────────────────┐
│              Level 1: Multi-Worker Uvicorn       │             │
│         (Simple --workers flag configuration)    │             │
└──────────────────────────────────────────────────────────────────┘
```

## The Four Levels

### [Level 1: Multi-Worker Uvicorn](level1-multi-worker.md)

**When to use**: You have a multi-core server and need better CPU utilization.

**What it does**: Runs multiple uvicorn worker processes that share incoming connections.

**Setup complexity**: ⭐ (Configuration only, no code changes)

**Performance**: 10-50K requests/second on 8-core machine

**Key features**:
- Simple `--workers N` flag
- Automatic load distribution across workers
- Each worker handles requests independently
- No shared state between workers

**Limitations**:
- No worker health monitoring
- No graceful restarts
- Manual process management

### [Level 2: Gunicorn Process Manager](level2-gunicorn.md)

**When to use**: You need production-grade reliability and zero-downtime deployments.

**What it does**: Gunicorn manages uvicorn workers with health monitoring and graceful restarts.

**Setup complexity**: ⭐⭐ (Add gunicorn.conf.py, update Dockerfile)

**Performance**: 50-100K requests/second with proper tuning

**Key features**:
- Worker health monitoring and auto-restart
- Graceful shutdown and reload (zero downtime)
- Worker recycling (prevents memory leaks)
- Configurable timeouts and connection limits
- Production-grade logging

**Advantages over Level 1**:
- Automatic worker restart on crashes
- `SIGHUP` for zero-downtime code reloads
- Better resource management
- Enhanced observability

### [Level 3: Background Task Processing](level3-background-tasks.md)

**When to use**: You have CPU-intensive or long-running operations that block request handling.

**What it does**: Offloads work to separate RQ worker processes backed by Redis.

**Setup complexity**: ⭐⭐⭐ (Add RQ workers, task definitions, monitoring)

**Performance**: Handles 1000+ concurrent background jobs

**Key features**:
- Async task execution with RQ (Redis Queue)
- Task persistence and retry logic
- Job prioritization and scheduling
- RQ Dashboard for monitoring
- Separate worker scaling independent of web workers

**Use cases**:
- Report generation
- Data export/import
- Email sending
- Image/video processing
- ML model inference
- Batch operations

### [Level 4: Horizontal Scaling](level4-horizontal-scaling.md)

**When to use**: Single-machine capacity is exhausted or you need high availability.

**What it does**: Distributes traffic across multiple servers using load balancers.

**Setup complexity**: ⭐⭐⭐⭐ (Infrastructure setup, orchestration plugins)

**Performance**: 100K+ requests/second across multiple nodes

**Key features**:
- Load balancer configuration (nginx/Traefik)
- **Kubernetes plugin** - `pip install -e ".[k8s]"`
- **Docker Swarm plugin** - `pip install -e ".[swarm]"`
- Session affinity and distributed caching
- Auto-scaling based on metrics
- Health check integration

**Plugins available**:
- **Kubernetes**: Full orchestration with `kubectl` integration
- **Docker Swarm**: Simpler orchestration for smaller deployments

## Configuration

All scaling settings are controlled via environment variables and configuration files:

### Environment Variables

```bash
# Level 1: Worker count
WORKERS=4  # Number of worker processes

# Level 2: Gunicorn settings (gunicorn.conf.py reads these)
WORKER_TIMEOUT=30
MAX_REQUESTS=1000
MAX_REQUESTS_JITTER=100

# Level 3: Background tasks
ENABLE_BACKGROUND_TASKS=true
REDIS_URL=redis://localhost:6379
TASK_BROKER_URL=redis://localhost:6379/1
TASK_RESULT_BACKEND=redis://localhost:6379/2

# Level 4: Distributed mode
ENABLE_DISTRIBUTED_MODE=true
SESSION_AFFINITY=true
SHARED_CACHE_URL=redis://localhost:6379/3
```

### Configuration Files

- `gunicorn.conf.py` - Gunicorn worker settings (Level 2)
- `docker-compose.yml` - Local multi-service setup (Level 3)
- `deployment/docker-compose.prod.yml` - Production compose (Levels 2-3)
- `deployment/nginx.conf` - Load balancer template (Level 4)
- `deployment/traefik.yml` - Alternative load balancer (Level 4)

## Decision Guide

**Choose your starting level:**

| Scenario | Recommended Level | Why |
|----------|------------------|-----|
| Development on laptop | Single worker | Fast reload, simple debugging |
| Staging environment | Level 1 | Multi-worker for realistic testing |
| Production < 10K req/sec | Level 2 | Gunicorn reliability without complexity |
| Long-running operations | Level 3 | Background tasks prevent request timeouts |
| Production > 50K req/sec | Level 2 + 3 | Worker scaling + task offloading |
| High availability required | Level 4 | Multi-node redundancy |
| Production > 100K req/sec | Level 4 | Horizontal scaling across machines |

**Progressive adoption path:**

1. **Start**: Single worker (development)
2. **Grow**: Level 1 when you deploy (simple multi-worker)
3. **Harden**: Level 2 when you need reliability (Gunicorn)
4. **Offload**: Level 3 when tasks block requests (RQ)
5. **Scale out**: Level 4 when single machine isn't enough (plugins)

## Performance Testing

We include load testing tools to measure performance at each level:

```bash
# Run load tests
make load-test LEVEL=1  # Test multi-worker
make load-test LEVEL=2  # Test gunicorn
make load-test LEVEL=3  # Test with background tasks
make load-test LEVEL=4  # Test distributed

# Generate performance report
make performance-report
```

See [load-testing.md](load-testing.md) for detailed testing procedures and benchmarks.

## Troubleshooting

Common issues and solutions are documented in [troubleshooting.md](troubleshooting.md):

- Worker health issues
- Memory leaks and worker recycling
- Task queue backlogs
- Load balancer configuration
- Session affinity problems
- Distributed caching issues

## Implementation Details

### Key Interfaces

**Worker Configuration** (`src/app/core/config.py`):
```python
class WorkerSettings(BaseSettings):
    """Worker and scaling configuration."""

    # Level 1: Uvicorn workers
    workers: int = 1
    worker_class: str = "uvicorn.workers.UvicornWorker"

    # Level 2: Gunicorn settings
    worker_timeout: int = 30
    max_requests: int = 1000
    max_requests_jitter: int = 100
    graceful_timeout: int = 30
    keepalive: int = 5

    # Level 3: Background tasks
    enable_background_tasks: bool = False
    task_broker_url: str = "redis://localhost:6379/1"
    task_result_backend: str = "redis://localhost:6379/2"

    # Level 4: Horizontal scaling
    enable_distributed_mode: bool = False
    session_affinity: bool = False
    shared_cache_url: str = "redis://localhost:6379/3"
```

**Task Queue Interface** (`src/app/services/tasks.py`):
```python
class TaskService(Protocol):
    """Protocol for background task execution."""

    async def enqueue_task(
        self,
        task_name: str,
        *args,
        **kwargs
    ) -> str:  # Returns task_id
        """Enqueue a background task."""
        ...

    async def get_task_status(self, task_id: str) -> dict:
        """Get status of a background task."""
        ...

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending/running task."""
        ...
```

**Health Check Interface** (`src/app/api/routes/health.py`):
```python
@router.get("/health/worker")
async def worker_health():
    """Worker-specific health check for load balancer."""
    return {
        "status": "healthy",
        "worker_id": os.getpid(),
        "uptime": get_worker_uptime(),
        "active_connections": get_active_connections()
    }
```

## Plugin System (Level 4)

Install optional orchestration plugins as needed:

### Kubernetes Plugin
```bash
# Install
pip install -e ".[k8s]"

# Deploy
python -m deployment.plugins.kubernetes deploy --namespace production

# Scale
python -m deployment.plugins.kubernetes scale --replicas 5

# Status
python -m deployment.plugins.kubernetes status
```

See [plugins/kubernetes/README.md](../../deployment/plugins/kubernetes/README.md)

### Docker Swarm Plugin
```bash
# Install
pip install -e ".[swarm]"

# Deploy
python -m deployment.plugins.swarm deploy --stack-name myapp

# Scale
python -m deployment.plugins.swarm scale --service web --replicas 3

# Status
python -m deployment.plugins.swarm status
```

See [plugins/swarm/README.md](../../deployment/plugins/swarm/README.md)

### Install All Scaling Features
```bash
# Install everything
pip install -e ".[all-scaling]"
```

This includes: RQ, RQ Dashboard, Gunicorn, psutil, Kubernetes client, Docker SDK

## Next Steps

1. **Read the level guides** - Start with [Level 1](level1-multi-worker.md)
2. **Test your setup** - Use [load testing](load-testing.md) to validate
3. **Monitor performance** - Set up metrics and dashboards
4. **Plan capacity** - Use benchmarks to size your infrastructure
5. **Review troubleshooting** - Familiarize yourself with [common issues](troubleshooting.md)

## References

- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [RQ (Redis Queue) Documentation](https://python-rq.org/)
- [Uvicorn Deployment](https://www.uvicorn.org/deployment/)
