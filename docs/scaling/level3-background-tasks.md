# Level 3: Background Task Processing

**Complexity**: ⭐⭐⭐ (Add RQ workers, task definitions, monitoring)
**Performance**: Handles 1000+ concurrent background jobs
**When to use**: You have CPU-intensive or long-running operations that block request handling

## Overview

Level 3 introduces **background task processing** using **RQ (Redis Queue)**, a simple Python task queue backed by Redis. This level solves a critical problem: offloading work that's too slow for the request-response cycle.

Without background tasks, long-running operations block your API workers, reducing throughput and causing timeouts. With RQ, you can enqueue work and return immediately, processing tasks asynchronously in separate worker processes.

## The Problem: Request Blocking

**Scenario without background tasks:**

```python
@app.post("/api/reports/generate")
async def generate_report(report_id: str):
    # This blocks the worker for 45 seconds!
    report_data = fetch_data_from_database()      # 10 seconds
    processed = process_and_aggregate(report_data)  # 30 seconds
    pdf = generate_pdf(processed)                  # 5 seconds

    return {"report": pdf}
    # Worker was blocked for 45 seconds
    # No other requests could be handled by this worker
```

**Problems:**
- ❌ Worker blocked for 45 seconds
- ❌ User waits 45 seconds for response
- ❌ Timeout if operation exceeds request timeout
- ❌ Reduced throughput (worker can't handle other requests)

**Solution with background tasks:**

```python
@app.post("/api/reports/generate")
async def generate_report(report_id: str, tasks: TaskService = Depends()):
    # Enqueue task and return immediately (< 100ms)
    task_id = await tasks.enqueue_task(
        "generate_report_task",
        report_id=report_id
    )

    return {
        "task_id": task_id,
        "status": "processing",
        "status_url": f"/api/tasks/{task_id}"
    }
    # Worker returns immediately
    # Task processes in background

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str, tasks: TaskService = Depends()):
    status = await tasks.get_task_status(task_id)
    return status  # {status: "completed", result: {...}}
```

**Benefits:**
- ✅ Worker returns in < 100ms
- ✅ User gets immediate response with task ID
- ✅ Task processes asynchronously in background
- ✅ Worker can handle other requests immediately
- ✅ No timeouts (task can run for hours if needed)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Gunicorn + Uvicorn Workers                 │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │            │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘            │ │
│  └───────┼─────────────┼─────────────┼───────────────────┘ │
│          │             │             │                      │
│          └─────────────┴─────────────┴──────────────────────┤
│                         Enqueue tasks                        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Redis (Queue)     │
                    │  • Task queue        │
                    │  • Task results      │
                    │  • Task metadata     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    RQ Workers        │
                    │  ┌────────────────┐  │
                    │  │ RQ Worker 1    │  │
                    │  │ • Polls queue  │  │
                    │  │ • Runs tasks   │  │
                    │  └────────────────┘  │
                    │  ┌────────────────┐  │
                    │  │ RQ Worker 2    │  │
                    │  └────────────────┘  │
                    │  ┌────────────────┐  │
                    │  │ RQ Worker N    │  │
                    │  └────────────────┘  │
                    └──────────────────────┘
```

**Flow:**
1. API endpoint receives request
2. Enqueues task to Redis queue (< 10ms)
3. Returns task ID immediately
4. RQ worker polls queue, picks up task
5. Worker executes task in background
6. Result stored in Redis
7. Client polls status endpoint to check progress

## Why RQ Over Celery?

We chose **RQ** for its ruthless simplicity:

| Feature | RQ | Celery |
|---------|------|--------|
| **Setup complexity** | ⭐ Simple | ⭐⭐⭐ Complex |
| **Configuration** | Minimal | Extensive |
| **Broker options** | Redis only | Redis, RabbitMQ, SQS, etc. |
| **Learning curve** | Gentle | Steep |
| **Monitoring** | RQ Dashboard (simple) | Flower (feature-rich) |
| **Use case** | Web app background tasks | Large-scale distributed systems |
| **Lines of code** | ~50 | ~200+ |

**Decision**: RQ aligns with our "ruthless simplicity" philosophy. For web backends, RQ's simplicity wins over Celery's power.

## Setup

### 1. Install RQ

Add to dependencies:

```bash
# Using uv
uv add rq rq-dashboard

# Or pip
pip install rq rq-dashboard
```

Already included in `pyproject.toml`:
```toml
[project.optional-dependencies]
scaling = [
    "rq>=2.0.0",
    "rq-dashboard>=0.7.0",
    "gunicorn>=23.0.0",
    "psutil>=7.1.0"
]
```

Install with:
```bash
pip install -e ".[scaling]"
```

### 2. Configure Environment

Update `.env`:

```bash
# Background Tasks (Level 3)
ENABLE_BACKGROUND_TASKS=true
REDIS_URL=redis://localhost:6379
TASK_BROKER_URL=redis://localhost:6379/1    # RQ queue
TASK_RESULT_BACKEND=redis://localhost:6379/2  # Results storage
```

### 3. Create Task Service Interface

Create `src/app/services/tasks.py`:

```python
"""Task service for background job processing."""

from typing import Protocol, Any
from redis import Redis
from rq import Queue
from rq.job import Job

class TaskService(Protocol):
    """Protocol for background task execution."""

    async def enqueue_task(
        self,
        task_name: str,
        *args,
        **kwargs
    ) -> str:
        """Enqueue a background task. Returns task_id."""
        ...

    async def get_task_status(self, task_id: str) -> dict:
        """Get status of a background task."""
        ...

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending/running task."""
        ...


class RQTaskService:
    """RQ-based task service implementation."""

    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url)
        self.queue = Queue(connection=self.redis)

    async def enqueue_task(
        self,
        task_name: str,
        *args,
        **kwargs
    ) -> str:
        """Enqueue a task and return task ID."""
        from app.tasks import TASK_REGISTRY

        task_func = TASK_REGISTRY.get(task_name)
        if not task_func:
            raise ValueError(f"Unknown task: {task_name}")

        job = self.queue.enqueue(task_func, *args, **kwargs)
        return job.id

    async def get_task_status(self, task_id: str) -> dict:
        """Get task status and result."""
        job = Job.fetch(task_id, connection=self.redis)

        return {
            "task_id": task_id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "result": job.result,
            "error": str(job.exc_info) if job.is_failed else None,
        }

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if it's pending."""
        try:
            job = Job.fetch(task_id, connection=self.redis)
            job.cancel()
            return True
        except Exception:
            return False
```

### 4. Define Tasks

Create `src/app/tasks/__init__.py`:

```python
"""Task definitions for background processing."""

import time
from typing import Dict, Callable

# Task registry
TASK_REGISTRY: Dict[str, Callable] = {}

def register_task(name: str):
    """Decorator to register a task."""
    def decorator(func):
        TASK_REGISTRY[name] = func
        return func
    return decorator


# Example tasks
@register_task("generate_report")
def generate_report_task(report_id: str) -> dict:
    """Generate a report (example long-running task)."""
    # Simulate heavy processing
    time.sleep(5)  # Fetch data
    time.sleep(30)  # Process and aggregate
    time.sleep(5)  # Generate PDF

    return {
        "report_id": report_id,
        "status": "completed",
        "url": f"/reports/{report_id}.pdf"
    }


@register_task("send_email")
def send_email_task(to: str, subject: str, body: str) -> dict:
    """Send email (example background task)."""
    # Send email via SMTP/API
    time.sleep(2)

    return {
        "to": to,
        "subject": subject,
        "sent_at": time.time()
    }


@register_task("process_upload")
def process_upload_task(file_path: str) -> dict:
    """Process uploaded file."""
    # Read file, validate, transform, store
    time.sleep(10)

    return {
        "file_path": file_path,
        "processed": True,
        "records": 1000
    }
```

### 5. Add Task API Endpoints

Create `src/app/api/routes/tasks.py`:

```python
"""Task management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from app.services.tasks import TaskService
from app.dependencies.services import get_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", status_code=202)
async def create_task(
    task_name: str,
    task_args: dict = None,
    tasks: TaskService = Depends(get_task_service)
):
    """Enqueue a background task."""
    try:
        task_id = await tasks.enqueue_task(
            task_name,
            **(task_args or {})
        )
        return {
            "task_id": task_id,
            "status": "queued",
            "status_url": f"/api/tasks/{task_id}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    tasks: TaskService = Depends(get_task_service)
):
    """Get task status and result."""
    try:
        status = await tasks.get_task_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    tasks: TaskService = Depends(get_task_service)
):
    """Cancel a pending task."""
    cancelled = await tasks.cancel_task(task_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    return {"status": "cancelled"}
```

### 6. Update Docker Compose

Add RQ worker service to `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WORKERS=4
      - ENABLE_BACKGROUND_TASKS=true
      - REDIS_URL=redis://redis:6379
      - TASK_BROKER_URL=redis://redis:6379/1
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
      - redis
    command: gunicorn app.main:create_app() --config gunicorn.conf.py

  # RQ Worker for background tasks
  worker:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379
      - TASK_BROKER_URL=redis://redis:6379/1
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
      - db
    command: rq worker --url redis://redis:6379/1
    deploy:
      replicas: 2  # Run 2 RQ workers

  # RQ Dashboard for monitoring
  rq-dashboard:
    build: .
    ports:
      - "9181:9181"
    environment:
      - RQ_DASHBOARD_REDIS_URL=redis://redis:6379/1
    depends_on:
      - redis
    command: rq-dashboard --redis-url redis://redis:6379/1

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

## Running Background Workers

### Start Workers

```bash
# Single worker
rq worker --url redis://localhost:6379/1

# Multiple workers
rq worker --url redis://localhost:6379/1 &
rq worker --url redis://localhost:6379/1 &
rq worker --url redis://localhost:6379/1 &

# With Docker Compose
docker-compose up worker
```

### Monitor with RQ Dashboard

```bash
# Start dashboard
rq-dashboard --redis-url redis://localhost:6379/1

# Or with Docker Compose
docker-compose up rq-dashboard

# Access at http://localhost:9181
```

Dashboard shows:
- Queued jobs
- Running jobs
- Failed jobs
- Worker status
- Job history

## Usage Examples

### Example 1: Generate Report

```python
# API endpoint
@app.post("/api/reports/generate")
async def generate_report(
    report_id: str,
    tasks: TaskService = Depends(get_task_service)
):
    task_id = await tasks.enqueue_task(
        "generate_report",
        report_id=report_id
    )

    return {
        "task_id": task_id,
        "status": "processing",
        "check_status": f"/api/tasks/{task_id}"
    }

# Client usage
response = requests.post("/api/reports/generate", json={"report_id": "123"})
task_id = response.json()["task_id"]

# Poll for completion
while True:
    status = requests.get(f"/api/tasks/{task_id}").json()
    if status["status"] == "finished":
        print("Report ready:", status["result"])
        break
    time.sleep(2)
```

### Example 2: Process File Upload

```python
@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile,
    tasks: TaskService = Depends(get_task_service)
):
    # Save file temporarily
    file_path = f"/tmp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Enqueue processing task
    task_id = await tasks.enqueue_task(
        "process_upload",
        file_path=file_path
    )

    return {
        "task_id": task_id,
        "message": "File uploaded, processing in background"
    }
```

### Example 3: Batch Operations

```python
@app.post("/api/users/notify-all")
async def notify_all_users(
    message: str,
    tasks: TaskService = Depends(get_task_service)
):
    users = get_all_users()  # Quick DB query

    # Enqueue email task for each user
    task_ids = []
    for user in users:
        task_id = await tasks.enqueue_task(
            "send_email",
            to=user.email,
            subject="Notification",
            body=message
        )
        task_ids.append(task_id)

    return {
        "message": f"Queued {len(task_ids)} emails",
        "task_ids": task_ids
    }
```

## Task Patterns

### Pattern 1: Long-Running Processing

```python
@register_task("data_export")
def export_data_task(user_id: str, format: str) -> dict:
    """Export user data (can take 10-60 minutes)."""
    data = fetch_all_user_data(user_id)      # 5 min
    processed = transform_data(data, format)  # 30 min
    file_url = upload_to_s3(processed)       # 5 min
    send_email_notification(user_id, file_url)  # 1 sec

    return {"file_url": file_url}
```

### Pattern 2: Scheduled Tasks

```python
from rq.decorators import job

@job('default', timeout=3600)
def cleanup_old_data():
    """Scheduled cleanup task (runs daily)."""
    deleted = delete_records_older_than(days=90)
    return {"deleted": deleted}

# Schedule with cron or RQ Scheduler
from rq_scheduler import Scheduler
scheduler = Scheduler(connection=redis)
scheduler.cron(
    "0 2 * * *",  # Run at 2 AM daily
    func=cleanup_old_data
)
```

### Pattern 3: Retry Logic

```python
from rq import Retry

@register_task("api_call")
def call_external_api_task(url: str) -> dict:
    """Call external API with automatic retry."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

# Enqueue with retry
job = queue.enqueue(
    call_external_api_task,
    url="https://api.example.com/data",
    retry=Retry(max=3, interval=[10, 30, 60])  # Retry 3 times with backoff
)
```

## Monitoring and Observability

### RQ Dashboard

Access at `http://localhost:9181`:

- **Queues**: View all queues and job counts
- **Workers**: See active workers and their status
- **Jobs**: Inspect individual jobs, view results/errors
- **Failed Jobs**: Retry or delete failed jobs

### Custom Metrics

```python
from prometheus_client import Counter, Histogram

task_enqueued = Counter('tasks_enqueued_total', 'Tasks enqueued', ['task_name'])
task_duration = Histogram('task_duration_seconds', 'Task duration', ['task_name'])

@register_task("monitored_task")
def monitored_task(data: dict) -> dict:
    task_enqueued.labels(task_name="monitored_task").inc()

    with task_duration.labels(task_name="monitored_task").time():
        # Do work
        result = process(data)

    return result
```

## Troubleshooting

### Issue 1: Tasks Not Processing

**Symptoms**: Jobs stay in queue, never execute

**Causes**:
- RQ workers not running
- Redis connection issue
- Wrong Redis database

**Solutions**:
```bash
# Check workers
docker-compose ps worker
# Should show "Up"

# Check Redis connection
redis-cli -u redis://localhost:6379/1 ping
# Should return "PONG"

# Verify queue
rq info --url redis://localhost:6379/1
# Shows queue stats
```

### Issue 2: Tasks Failing Silently

**Symptoms**: Tasks marked as failed, no clear error

**Causes**:
- Exception in task code
- Missing dependencies in worker environment

**Solutions**:
```python
# Add logging to tasks
import logging
logger = logging.getLogger(__name__)

@register_task("failing_task")
def failing_task(data: dict) -> dict:
    try:
        logger.info(f"Processing: {data}")
        result = process(data)
        logger.info(f"Completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        raise  # Re-raise so RQ marks as failed
```

### Issue 3: Worker Memory Leaks

**Symptoms**: Worker memory grows over time

**Causes**:
- Large task results stored in memory
- Circular references

**Solutions**:
```python
# Use job TTL to clean up results
job = queue.enqueue(
    task_func,
    result_ttl=3600  # Delete result after 1 hour
)

# Or configure default TTL
queue = Queue(connection=redis, default_timeout=3600)
```

### Issue 4: Redis Connection Pool Exhaustion

**Symptoms**: "ConnectionError: Too many connections"

**Causes**:
- Each worker creates Redis connections
- Not closing connections properly

**Solutions**:
```python
# Configure connection pool
from redis import ConnectionPool

pool = ConnectionPool.from_url(
    redis_url,
    max_connections=50  # Increase pool size
)
redis = Redis(connection_pool=pool)
queue = Queue(connection=redis)
```

## Best Practices

### 1. Design Tasks to Be Idempotent

```python
# ✅ Good: Idempotent (safe to retry)
@register_task("send_email_idempotent")
def send_email(user_id: str, template: str):
    # Check if already sent
    if email_already_sent(user_id, template):
        return {"status": "already_sent"}

    # Send and record
    send_email_via_api(user_id, template)
    record_email_sent(user_id, template)

# ❌ Bad: Not idempotent (retry causes duplicates)
@register_task("send_email_bad")
def send_email(user_id: str, template: str):
    send_email_via_api(user_id, template)  # Resend on retry!
```

### 2. Set Appropriate Timeouts

```python
# Short tasks
@register_task("quick_task")
@job('default', timeout=30)  # 30 seconds max
def quick_task():
    pass

# Long tasks
@register_task("long_task")
@job('default', timeout=3600)  # 1 hour max
def long_task():
    pass
```

### 3. Use Result TTL

```python
# Don't store results forever
job = queue.enqueue(
    task_func,
    result_ttl=3600  # Results expire after 1 hour
)
```

### 4. Handle Task Failures Gracefully

```python
@register_task("resilient_task")
def resilient_task(data: dict) -> dict:
    try:
        return process(data)
    except RecoverableError as e:
        # Log and continue
        logger.warning(f"Recoverable error: {e}")
        return {"status": "partial", "error": str(e)}
    except CriticalError as e:
        # Log and fail
        logger.error(f"Critical error: {e}", exc_info=True)
        raise  # Fail the task
```

### 5. Monitor Queue Depth

```bash
# Alert if queue > 1000 jobs
rq info --url redis://localhost:6379/1 | grep "jobs in queue"
```

## Performance Tuning

### Worker Count

**Formula**: Start with `workers = CPU cores ÷ 2`

```bash
# 8-core server
RQ_WORKERS=4

# Scale based on task type:
# - I/O bound tasks: More workers (2x cores)
# - CPU bound tasks: Fewer workers (1x cores)
```

### Queue Prioritization

```python
# Create priority queues
high_priority = Queue('high', connection=redis)
low_priority = Queue('low', connection=redis)

# Enqueue to appropriate queue
high_priority.enqueue(critical_task)
low_priority.enqueue(background_cleanup)

# Start workers with priority
rq worker high low  # Processes 'high' first
```

## When to Move to Level 4

Consider Level 4 (Horizontal Scaling) when:
- Single server capacity exhausted (> 100K req/sec)
- Need high availability across multiple servers
- Want geographic distribution
- Require automatic failover

## Next Steps

1. **Add background tasks** - Identify slow operations
2. **Monitor task queue** - Use RQ Dashboard
3. **Tune worker count** - Match workload characteristics
4. **Set up alerts** - Monitor queue depth and failures
5. **Consider Level 4** - When single-server capacity isn't enough

Ready to scale across multiple servers? See [Level 4: Horizontal Scaling](level4-horizontal-scaling.md).

## References

- [RQ Documentation](https://python-rq.org/)
- [RQ Dashboard](https://github.com/Parallels/rq-dashboard)
- [Redis Queue Patterns](https://redis.io/docs/manual/patterns/distributed-locks/)
- [Background Jobs Best Practices](https://devcenter.heroku.com/articles/background-jobs-queueing)
