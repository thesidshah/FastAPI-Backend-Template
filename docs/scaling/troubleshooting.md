# Troubleshooting Guide

This guide covers common issues encountered when scaling the production-fastapi-backend application, organized by scaling level and symptom.

## Quick Diagnosis Table

| Symptom | Likely Cause | Quick Fix | See Section |
|---------|-------------|-----------|-------------|
| Application won't start | Port in use | `lsof -i :8000` and kill process | [Startup Issues](#startup-issues) |
| Only one worker running | Missing `--workers` flag | Add `--workers 4` | [Level 1 Issues](#level-1-multi-worker-issues) |
| Workers crash frequently | Memory leak or timeout | Increase timeout, enable recycling | [Worker Crashes](#worker-crashes) |
| "Too many connections" | DB pool exhaustion | Reduce pool size per worker | [Database Issues](#database-connection-issues) |
| Tasks not processing | RQ workers not running | Start RQ workers | [Level 3 Issues](#level-3-background-task-issues) |
| Uneven load distribution | Wrong LB algorithm | Use `least_conn` not `ip_hash` | [Level 4 Issues](#level-4-horizontal-scaling-issues) |
| High memory usage | Memory leak in application | Enable worker recycling | [Memory Issues](#memory-issues) |
| Slow response times | Database query issues | Add indexes, use connection pooling | [Performance Issues](#performance-issues) |

## Startup Issues

### Issue: Application Won't Start

**Symptoms:**
```
ERROR: [Errno 48] Address already in use
```

**Cause:** Port 8000 already in use by another process

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn app.main:create_app --factory --port 8001
```

### Issue: Import Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'app'
```

**Cause:** PYTHONPATH not set correctly

**Solution:**
```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/production-fastapi-backend/src

# Or use absolute imports in Docker
ENV PYTHONPATH=/app/src
```

### Issue: Database Connection Refused

**Symptoms:**
```
ERROR: could not connect to server: Connection refused
```

**Cause:** PostgreSQL not running or wrong connection string

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps db

# Start database
docker-compose up -d db

# Verify connection string
echo $DATABASE_URL
# Should be: postgresql://user:pass@host:5432/dbname

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

## Level 1: Multi-Worker Issues

### Issue: Only One Worker Running

**Symptoms:**
- `ps aux | grep uvicorn` shows only one process
- Performance doesn't improve with `--workers` flag

**Cause:** `--reload` flag conflicts with `--workers`

**Solution:**
```bash
# ❌ Bad: reload disables multi-worker
uvicorn app.main:create_app --factory --workers 4 --reload

# ✅ Good: remove reload for production
uvicorn app.main:create_app --factory --workers 4
```

### Issue: Inconsistent Responses

**Symptoms:**
- Same request returns different results
- Session data lost between requests

**Cause:** Workers have independent memory (in-memory state not shared)

**Solution:**
```python
# ❌ Bad: In-memory state (not shared across workers)
user_sessions = {}

# ✅ Good: Redis-backed state (shared)
from redis import Redis
redis = Redis.from_url(os.getenv("REDIS_URL"))

def get_session(session_id):
    return redis.get(f"session:{session_id}")
```

### Issue: Worker Count Auto-Detection Wrong

**Symptoms:**
- `--workers 0` creates too many/few workers
- System becomes slow with auto-detected workers

**Cause:** CPU count doesn't match optimal worker count

**Solution:**
```bash
# Manually specify workers based on your workload
# I/O-bound: workers = CPU cores × 2
# CPU-bound: workers = CPU cores

# 8-core server, I/O-bound workload
uvicorn app.main:create_app --factory --workers 16

# 8-core server, CPU-bound workload
uvicorn app.main:create_app --factory --workers 8
```

## Level 2: Gunicorn Issues

### Issue: Workers Timing Out

**Symptoms:**
```
[CRITICAL] WORKER TIMEOUT (pid:1234)
[INFO] Worker with pid 1234 was terminated due to signal 9
```

**Cause:** Worker silent for longer than `timeout` setting

**Solution:**
```python
# gunicorn.conf.py
# Increase timeout for slow operations
timeout = 60  # Instead of default 30

# Or fix the slow operation:
# - Add database indexes
# - Use async HTTP clients
# - Offload to background tasks (Level 3)
```

### Issue: Zero-Downtime Reload Not Working

**Symptoms:**
- `kill -HUP <pid>` doesn't reload code
- Must restart to see code changes

**Cause:** `preload_app = True` prevents reload

**Solution:**
```python
# gunicorn.conf.py
preload_app = False  # Allow code reload

# Then reload with
kill -HUP <master-pid>
# Or
docker-compose kill -s HUP web
```

### Issue: Workers Not Restarting

**Symptoms:**
- Crashed workers stay dead
- Worker count decreases over time

**Cause:** Gunicorn master process not monitoring workers

**Solution:**
```bash
# Check if master process is running
ps aux | grep gunicorn | grep master

# If not running, start Gunicorn properly
gunicorn app.main:create_app() --config gunicorn.conf.py

# Verify workers are managed
ps aux | grep gunicorn
# Should show: 1 master + N workers
```

### Issue: High Memory Usage with Gunicorn

**Symptoms:**
- Memory usage grows continuously
- Eventually OOM (Out of Memory) errors

**Cause:** Memory leaks in application code

**Solution:**
```python
# gunicorn.conf.py
# Enable worker recycling to mitigate leaks
max_requests = 1000  # Restart worker after 1000 requests
max_requests_jitter = 100  # Add randomness

# Also fix the leak:
# - Check for circular references
# - Close database connections properly
# - Clear large variables after use
```

## Level 3: Background Task Issues

### Issue: Tasks Not Processing

**Symptoms:**
- Tasks stay in "queued" status forever
- Queue depth keeps growing

**Cause:** RQ workers not running

**Solution:**
```bash
# Check if workers are running
docker-compose ps worker
# Should show "Up"

# Start workers
docker-compose up -d worker

# Verify workers are processing
rq info --url redis://localhost:6379/1
# Should show active workers
```

### Issue: Tasks Failing Silently

**Symptoms:**
- Tasks marked as "failed" with no error message
- RQ Dashboard shows failures but no details

**Cause:** Exception in task code not being logged

**Solution:**
```python
# Add logging to task
import logging
logger = logging.getLogger(__name__)

@register_task("my_task")
def my_task(data: dict) -> dict:
    try:
        logger.info(f"Processing task: {data}")
        result = process(data)
        logger.info(f"Task completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        raise  # Re-raise so RQ marks as failed
```

### Issue: RQ Workers Consuming Too Much Memory

**Symptoms:**
- Worker memory grows over time
- Workers crash with OOM

**Cause:** Task results stored in memory indefinitely

**Solution:**
```python
# Set result TTL (time-to-live)
job = queue.enqueue(
    task_func,
    result_ttl=3600  # Results expire after 1 hour
)

# Or configure queue default
from rq import Queue
queue = Queue(connection=redis, default_timeout=3600)
```

### Issue: Redis Connection Pool Exhausted

**Symptoms:**
```
redis.exceptions.ConnectionError: Too many connections
```

**Cause:** Each worker creates too many Redis connections

**Solution:**
```python
# Configure connection pool
from redis import ConnectionPool, Redis

pool = ConnectionPool.from_url(
    redis_url,
    max_connections=50  # Increase pool size
)

redis = Redis(connection_pool=pool)
queue = Queue(connection=redis)
```

### Issue: Tasks Stuck in "Started" Status

**Symptoms:**
- Tasks never complete
- Worker appears to hang

**Cause:** Long-running task exceeds timeout

**Solution:**
```python
# Increase task timeout
from rq.decorators import job

@job('default', timeout=3600)  # 1 hour timeout
def long_running_task():
    # Process for a long time
    pass

# Or when enqueueing
job = queue.enqueue(
    long_running_task,
    timeout=3600
)
```

## Level 4: Horizontal Scaling Issues

### Issue: Uneven Load Distribution

**Symptoms:**
- One node handles most traffic
- Other nodes mostly idle

**Cause:** Session affinity or wrong LB algorithm

**Solution:**
```nginx
# nginx.conf
# Use least_conn instead of ip_hash
upstream backend {
    least_conn;  # Not ip_hash
    server node1:8000;
    server node2:8000;
    server node3:8000;
}
```

### Issue: Nodes Out of Sync

**Symptoms:**
- Different data on different nodes
- Inconsistent responses

**Cause:** Local state instead of shared state

**Solution:**
```python
# ❌ Bad: Local caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_config():
    return load_config()

# ✅ Good: Shared Redis cache
async def get_config():
    cached = await redis.get("config")
    if cached:
        return json.loads(cached)

    config = load_config()
    await redis.set("config", json.dumps(config), ex=3600)
    return config
```

### Issue: Load Balancer Health Checks Failing

**Symptoms:**
- Nodes marked as unhealthy
- Traffic not distributed to healthy nodes

**Cause:** Health check endpoint not responding

**Solution:**
```python
# Ensure health check endpoint exists
@app.get("/health")
async def health():
    return {"status": "healthy"}

# For readiness checks (K8s)
@app.get("/health/ready")
async def readiness():
    # Check dependencies
    try:
        await db.execute("SELECT 1")
        await redis.ping()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

```nginx
# nginx health check config
upstream backend {
    server node1:8000 max_fails=3 fail_timeout=30s;
    server node2:8000 max_fails=3 fail_timeout=30s;
}
```

### Issue: Kubernetes Pods Not Scaling

**Symptoms:**
- HPA (Horizontal Pod Autoscaler) not creating new pods
- Pods stay at minimum replica count

**Cause:** Metrics server not installed or metrics not available

**Solution:**
```bash
# Check if metrics-server is running
kubectl get deployment metrics-server -n kube-system

# Install if missing
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify metrics are available
kubectl top pods -n production

# Check HPA status
kubectl get hpa -n production
kubectl describe hpa fastapi-backend-hpa -n production
```

### Issue: Docker Swarm Services Not Starting

**Symptoms:**
- `docker service ls` shows 0/3 replicas
- Services stuck in "preparing" state

**Cause:** Image not available on all nodes or resource constraints

**Solution:**
```bash
# Check service status
docker service ps fastapi-backend --no-trunc

# Check logs
docker service logs fastapi-backend

# Verify image is on all nodes
docker images | grep fastapi-backend

# If missing, pull on all nodes
docker pull your-registry.com/fastapi-backend:latest

# Check resource availability
docker node ls
docker node inspect <node-id>
```

## Database Connection Issues

### Issue: "Too Many Connections"

**Symptoms:**
```
OperationalError: FATAL: too many connections for role "app"
```

**Cause:** Each worker × each node creates connections, exceeding database max

**Solution:**
```python
# Calculate connections needed:
# total = nodes × workers_per_node × pool_size_per_worker

# Reduce pool size per worker
# config.py
import multiprocessing

workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2))
nodes = int(os.getenv("NODE_COUNT", 1))

# Adjust pool size based on total workers
pool_size = max(5, 100 // (workers * nodes))

DATABASE_URL = (
    f"postgresql+asyncpg://...?"
    f"pool_size={pool_size}&"
    f"max_overflow=10"
)
```

Or increase database max connections:
```sql
-- PostgreSQL
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
```

### Issue: Connection Pool Exhausted

**Symptoms:**
```
TimeoutError: QueuePool limit of size 10 overflow 20 reached
```

**Cause:** Not releasing connections properly or pool too small

**Solution:**
```python
# Check for connections not being closed
async with db.begin():
    await db.execute(query)  # Auto-closes

# Or increase pool size
DATABASE_URL = "postgresql://...?pool_size=20&max_overflow=40"

# Monitor connection usage
@app.middleware("http")
async def log_db_connections(request, call_next):
    pool = request.app.state.db.engine.pool
    logger.info(f"DB pool: {pool.size()}/{pool.size() + pool.overflow()}")
    response = await call_next(request)
    return response
```

### Issue: Slow Database Queries

**Symptoms:**
- High latency under load
- Database CPU at 100%

**Cause:** Missing indexes or inefficient queries

**Solution:**
```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct
FROM pg_stats
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  AND n_distinct > 100
  AND tablename NOT IN (
    SELECT tablename
    FROM pg_indexes
    WHERE indexdef LIKE '%' || attname || '%'
  );

-- Add indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_user_id ON orders(user_id);
```

## Memory Issues

### Issue: Memory Leaks

**Symptoms:**
- Memory usage grows continuously
- Eventually OOM errors

**Cause:** Circular references, unclosed resources, or caching issues

**Solution:**
```python
# Use worker recycling (mitigation)
# gunicorn.conf.py
max_requests = 500  # Recycle more frequently

# Find leaks with memory profiler
from memory_profiler import profile

@profile
def potential_leak():
    # This function's memory usage will be tracked
    pass

# Check for circular references
import gc
gc.set_debug(gc.DEBUG_LEAK)

# Close resources properly
async with db.begin() as conn:
    # Connection auto-closed
    pass

# Clear large objects
del large_object
gc.collect()
```

### Issue: High Memory Usage Per Worker

**Symptoms:**
- Each worker uses > 500MB RAM
- Can't run many workers due to memory

**Cause:** Loading large datasets into memory

**Solution:**
```python
# ❌ Bad: Load entire dataset
users = await db.execute("SELECT * FROM users").fetchall()

# ✅ Good: Use pagination/streaming
async for batch in db.stream("SELECT * FROM users"):
    process_batch(batch)

# ✅ Good: Use generators
async def get_users():
    async for row in db.stream_query("SELECT * FROM users"):
        yield row

# Reduce worker memory footprint
# - Use connection pooling (share connections)
# - Don't cache large objects in worker memory
# - Stream large responses
```

## Performance Issues

### Issue: High Latency

**Symptoms:**
- p95 latency > 500ms
- Slow responses under load

**Cause:** Synchronous operations in async context, slow DB queries, or N+1 queries

**Solution:**
```python
# Find slow endpoints with middleware
import time

@app.middleware("http")
async def log_timing(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    if duration > 0.5:  # Log slow requests
        logger.warning(f"Slow request: {request.url.path} took {duration:.2f}s")

    return response

# Fix N+1 queries
# ❌ Bad: N+1 query
users = await db.execute("SELECT * FROM users").fetchall()
for user in users:
    orders = await db.execute(
        "SELECT * FROM orders WHERE user_id = ?", user.id
    ).fetchall()

# ✅ Good: Join or prefetch
results = await db.execute("""
    SELECT u.*, o.*
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
""").fetchall()
```

### Issue: Low Throughput

**Symptoms:**
- Can't exceed X req/sec even with more workers
- CPU not fully utilized

**Cause:** Bottleneck elsewhere (database, external API, GIL)

**Solution:**
```bash
# Profile to find bottleneck
pip install py-spy

# Profile running application
py-spy top --pid <worker-pid>

# Generate flamegraph
py-spy record -o profile.svg -- python -m uvicorn app.main:app

# Common bottlenecks:
# - Database: Add read replicas, caching
# - External API: Use async HTTP clients, caching
# - CPU-bound Python: Use Cython, offload to C extension
# - GIL: Use multiprocessing (already done with workers)
```

## Debugging Tools

### Application-Level

```python
# Request tracking
import uuid
from fastapi import Request

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    logger.info(f"Request started: {request_id} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Request finished: {request_id}")

    response.headers["X-Request-ID"] = request_id
    return response
```

### System-Level

```bash
# CPU usage
htop

# Memory usage
free -h
vmstat 1

# Disk I/O
iotop

# Network
iftop
netstat -an | grep :8000

# Process tree
pstree -p <gunicorn-master-pid>
```

### Docker-Level

```bash
# Container stats
docker stats

# Container logs
docker logs -f production-fastapi-backend

# Container resource limits
docker inspect production-fastapi-backend | grep -A 10 Resources

# Execute command in container
docker exec -it production-fastapi-backend bash
```

### Database-Level

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Slow queries
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '5 seconds';

-- Lock conflicts
SELECT blocked.pid, blocked.query, blocking.pid AS blocking_pid, blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid));

-- Table bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

## Getting Help

If you're still stuck after trying these solutions:

1. **Check logs**: Application, system, database, load balancer
2. **Collect metrics**: CPU, memory, network, disk, database connections
3. **Run load test**: Reproduce issue under controlled conditions
4. **Enable debug logging**: Set `LOG_LEVEL=debug`
5. **Create minimal reproduction**: Simplify to smallest failing case

**Ask for help with**:
- Exact error message
- Logs showing the issue
- Steps to reproduce
- What you've already tried
- Your configuration (gunicorn.conf.py, docker-compose.yml, etc.)

## Prevention

### Monitoring

Set up monitoring to catch issues early:

```python
from prometheus_client import Counter, Histogram

# Request metrics
request_count = Counter('requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('request_duration_seconds', 'Request duration')

# Database metrics
db_query_duration = Histogram('db_query_duration_seconds', 'DB query duration')
db_connections = Gauge('db_connections_active', 'Active DB connections')

# Worker metrics
worker_memory = Gauge('worker_memory_bytes', 'Worker memory usage')
worker_cpu = Gauge('worker_cpu_percent', 'Worker CPU usage')
```

### Alerting

Set alerts for critical issues:

```yaml
# Prometheus alerts
groups:
  - name: fastapi-backend
    rules:
      - alert: HighErrorRate
        expr: rate(requests_total{status=~"5.."}[5m]) > 0.01
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, request_duration_seconds) > 0.5
        annotations:
          summary: "High latency detected (p95 > 500ms)"

      - alert: DatabaseConnectionsHigh
        expr: db_connections_active > 80
        annotations:
          summary: "Database connections near limit"
```

### Regular Maintenance

```bash
# Weekly tasks
- Review slow query logs
- Check for memory leaks
- Analyze error logs
- Update dependencies

# Monthly tasks
- Load test to verify capacity
- Review and optimize database indexes
- Check disk space and clean up logs
- Review and update monitoring dashboards
```

## Related Guides

- [Level 1: Multi-Worker](level1-multi-worker.md)
- [Level 2: Gunicorn](level2-gunicorn.md)
- [Level 3: Background Tasks](level3-background-tasks.md)
- [Level 4: Horizontal Scaling](level4-horizontal-scaling.md)
- [Load Testing](load-testing.md)
