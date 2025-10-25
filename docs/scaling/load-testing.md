# Load Testing Guide

This guide covers performance testing strategies for each scaling level, tools to use, and how to interpret results.

## Philosophy

**Measure first, optimize second.** Don't guess at performance bottlenecks - measure them with real data.

**Progressive testing:** Test each scaling level before moving to the next. This establishes baseline performance and identifies which optimizations provide the most value.

## Testing Tools

### 1. siege (Simple HTTP Testing)

**Best for**: Quick smoke tests, basic throughput measurement

```bash
# Install
apt-get install siege  # or brew install siege

# Basic load test: 50 concurrent users for 30 seconds
siege -c 50 -t 30s http://localhost:8000/api/health

# Output shows:
# Transactions: 12,450 hits
# Availability: 100.00 %
# Response time: 0.12 secs
# Transaction rate: 415.00 trans/sec
```

**Advantages**:
- Simple to use
- Quick results
- Good for basic testing

**Limitations**:
- Limited reporting
- No custom scenarios
- Basic metrics only

### 2. Locust (Python-Based Load Testing)

**Best for**: Complex scenarios, realistic user behavior

```bash
# Install
pip install locust

# Run
locust -f tests/load/locustfile.py --host http://localhost:8000
```

Example `locustfile.py`:

```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    @task(3)  # Weight: 3x more likely than other tasks
    def get_users(self):
        self.client.get("/api/users")

    @task(2)
    def get_user(self):
        self.client.get("/api/users/123")

    @task(1)
    def create_user(self):
        self.client.post("/api/users", json={
            "name": "Test User",
            "email": "test@example.com"
        })

    def on_start(self):
        """Login once per user"""
        response = self.client.post("/api/auth/login", json={
            "username": "test",
            "password": "password"
        })
        self.token = response.json()["token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
```

**Advantages**:
- Python-based (easy to customize)
- Web UI for real-time monitoring
- Complex user scenarios
- Distributed testing support

**Usage**:
```bash
# Start web UI
locust -f locustfile.py --host http://localhost:8000

# Headless mode (CI/CD)
locust -f locustfile.py \
  --host http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless
```

### 3. k6 (Modern Load Testing)

**Best for**: CI/CD integration, detailed metrics

```bash
# Install
brew install k6  # or download from k6.io

# Run
k6 run tests/load/k6-script.js
```

Example `k6-script.js`:

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 20 },  // Ramp up to 20 users
    { duration: '1m', target: 50 },   // Stay at 50 users
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% < 500ms
    http_req_failed: ['rate<0.01'],    // Error rate < 1%
  },
};

export default function () {
  // Login
  let loginRes = http.post('http://localhost:8000/api/auth/login', {
    username: 'test',
    password: 'password',
  });

  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  let token = loginRes.json('token');

  // Get users
  let headers = { Authorization: `Bearer ${token}` };
  let res = http.get('http://localhost:8000/api/users', { headers });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  });

  sleep(1);
}
```

**Advantages**:
- JavaScript-based
- Excellent reporting
- CI/CD friendly (exit codes, JSON output)
- Built-in thresholds

**Usage**:
```bash
# Basic run
k6 run k6-script.js

# With output to InfluxDB
k6 run --out influxdb=http://localhost:8086/k6 k6-script.js

# Cloud run
k6 cloud k6-script.js
```

### 4. wrk (High-Performance Benchmarking)

**Best for**: Maximum throughput testing, low overhead

```bash
# Install
brew install wrk

# Run: 12 threads, 400 connections, 30 seconds
wrk -t12 -c400 -d30s http://localhost:8000/api/health

# Output:
# Running 30s test @ http://localhost:8000/api/health
#   12 threads and 400 connections
#   Thread Stats   Avg      Stdev     Max   +/- Stdev
#     Latency    10.15ms    5.23ms  50.12ms   68.42%
#     Req/Sec     3.25k   411.23     4.12k    71.23%
#   1,165,432 requests in 30.01s, 245.12MB read
# Requests/sec:  38,834.56
# Transfer/sec:      8.17MB
```

**Advantages**:
- Fastest tool (written in C)
- Minimal overhead
- Simple to use

**Limitations**:
- No custom scenarios
- Linux/macOS only

## Testing Methodology

### Baseline Testing (Level 0)

Test single-worker performance to establish baseline:

```bash
# Start single worker
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000

# Test simple endpoint
siege -c 50 -t 60s http://localhost:8000/api/health

# Test database-heavy endpoint
siege -c 50 -t 60s http://localhost:8000/api/users

# Record results:
# - Simple endpoint: ~X req/sec
# - DB endpoint: ~Y req/sec
```

### Level 1 Testing (Multi-Worker)

Test scaling improvement with multiple workers:

```bash
# Start with 4 workers
uvicorn app.main:create_app --factory --workers 4

# Run same tests
siege -c 50 -t 60s http://localhost:8000/api/health
siege -c 50 -t 60s http://localhost:8000/api/users

# Expected improvement: ~3-4x baseline
# Actual improvement: ~X.Xx baseline
```

### Level 2 Testing (Gunicorn)

Test production configuration:

```bash
# Start with Gunicorn
gunicorn app.main:create_app() --config gunicorn.conf.py

# Same tests
siege -c 50 -t 60s http://localhost:8000/api/health

# Should be similar to Level 1
# Additional test: Zero-downtime reload during load test
siege -c 50 -t 120s http://localhost:8000/api/health &
sleep 30
docker-compose kill -s HUP web  # Reload while under load
# Check: No failed requests during reload
```

### Level 3 Testing (Background Tasks)

Test task queue throughput:

```python
# Create load test for task enqueueing
from locust import HttpUser, task

class TaskUser(HttpUser):
    @task
    def enqueue_task(self):
        self.client.post("/api/tasks", json={
            "task_name": "generate_report",
            "task_args": {"report_id": "123"}
        })

# Run
locust -f task_load_test.py --users 100 --spawn-rate 10
```

Measure:
- Task enqueue rate (should be high: 1000+ tasks/sec)
- Task processing rate (depends on task complexity)
- Queue depth over time (should stay low if workers keep up)

### Level 4 Testing (Horizontal Scaling)

Test multi-node performance:

```bash
# Test load balancer distribution
for i in {1..1000}; do
  curl -s http://load-balancer/api/health/worker | jq -r .node_id
done | sort | uniq -c

# Should show even distribution across nodes

# Full load test
siege -c 200 -t 120s http://load-balancer/api/users

# Expected: ~(num_nodes × Level 2 performance)
# Actual efficiency: ~90-95%
```

## Test Scenarios

### Scenario 1: Ramp-Up Test

Gradually increase load to find breaking point:

```javascript
// k6 ramp-up
export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 300 },
    { duration: '5m', target: 400 },
    { duration: '2m', target: 500 },
    { duration: '5m', target: 500 },
    { duration: '2m', target: 0 },
  ],
};

// Watch for:
// - At what user count does latency spike?
// - At what user count do errors appear?
// - At what user count does throughput plateau?
```

### Scenario 2: Spike Test

Sudden traffic burst:

```javascript
export let options = {
  stages: [
    { duration: '30s', target: 50 },   // Normal
    { duration: '10s', target: 500 },  // Sudden spike
    { duration: '1m', target: 500 },   // Sustained
    { duration: '10s', target: 50 },   // Back to normal
    { duration: '30s', target: 50 },
  ],
};

// Tests:
// - How quickly does system recover?
// - Does it handle spike gracefully?
// - Are there any cascading failures?
```

### Scenario 3: Stress Test

Push beyond normal capacity:

```javascript
export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 300 },
    { duration: '5m', target: 500 },   // Beyond capacity
    { duration: '10m', target: 1000 }, // Way beyond
    { duration: '3m', target: 0 },
  ],
};

// Identify:
// - System limits
// - Failure modes
// - Recovery behavior
```

### Scenario 4: Soak Test

Sustained load over time:

```javascript
export let options = {
  stages: [
    { duration: '5m', target: 200 },
    { duration: '8h', target: 200 },  // 8 hours sustained
    { duration: '5m', target: 0 },
  ],
};

// Detects:
// - Memory leaks
// - Connection pool exhaustion
// - Gradual performance degradation
```

## Metrics to Track

### Application Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter('http_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'Request duration', ['method', 'endpoint'])

# System metrics
worker_count = Gauge('gunicorn_workers', 'Number of workers')
active_connections = Gauge('active_connections', 'Active connections')

# Business metrics
users_created = Counter('users_created_total', 'Users created')
reports_generated = Counter('reports_generated_total', 'Reports generated')
```

### Infrastructure Metrics

Monitor during load tests:
- **CPU usage**: `htop` or cloud metrics
- **Memory usage**: Watch for leaks
- **Network I/O**: Bandwidth saturation?
- **Database connections**: Pool exhaustion?
- **Disk I/O**: Bottleneck?

### Key Performance Indicators

| Metric | Target | Level 1 | Level 2 | Level 3 | Level 4 |
|--------|--------|---------|---------|---------|---------|
| **p50 latency** | < 50ms | ✅ | ✅ | ✅ | ✅ |
| **p95 latency** | < 200ms | ✅ | ✅ | ✅ | ⚠️ |
| **p99 latency** | < 500ms | ⚠️ | ✅ | ✅ | ⚠️ |
| **Throughput** | > 10K req/s | ❌ | ✅ | ✅ | ✅ |
| **Error rate** | < 0.1% | ✅ | ✅ | ✅ | ✅ |
| **Availability** | > 99.9% | ❌ | ⚠️ | ✅ | ✅ |

## Interpreting Results

### Good Signs

✅ **Linear scaling**: 4 workers = ~4x performance
✅ **Low error rate**: < 0.1% errors under load
✅ **Stable latency**: p99 doesn't spike dramatically
✅ **Quick recovery**: Returns to normal after spike
✅ **Even distribution**: All nodes/workers handle similar load

### Warning Signs

⚠️ **Sub-linear scaling**: 4 workers = 2x performance (bottleneck somewhere)
⚠️ **Increasing error rate**: Errors grow with load
⚠️ **Latency spikes**: p99 jumps 10x at high load
⚠️ **Slow recovery**: Takes minutes to stabilize after spike
⚠️ **Uneven distribution**: One node handles 80% of requests

### Red Flags

🚨 **Cascading failures**: Errors cause more errors
🚨 **Memory leaks**: Memory usage grows continuously
🚨 **Connection exhaustion**: "Too many connections" errors
🚨 **Complete failure**: System becomes unresponsive
🚨 **Data corruption**: Incorrect results under load

## Example: Full Test Suite

```bash
#!/bin/bash
# scripts/benchmark.sh - Complete performance test

set -e

echo "=== Production FastAPI Backend Performance Test ==="

# Function to run test and extract metrics
run_test() {
    local name=$1
    local url=$2
    local concurrency=$3

    echo ""
    echo "--- Testing: $name (concurrency: $concurrency) ---"

    siege -c $concurrency -t 60s -q $url 2>&1 | \
        grep -E "(Transactions|Availability|Response time|Transaction rate)"
}

# Start services
echo "Starting services..."
docker-compose up -d
sleep 10

echo ""
echo "=== LEVEL 1: Multi-Worker (4 workers) ==="
run_test "Health Check" "http://localhost:8000/health" 50
run_test "Database Query" "http://localhost:8000/api/users" 50

echo ""
echo "=== LEVEL 3: Background Tasks ==="
run_test "Task Enqueue" "http://localhost:8000/api/tasks" 100

# Cleanup
docker-compose down
```

Run:
```bash
chmod +x scripts/benchmark.sh
./scripts/benchmark.sh
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Performance Test

on:
  pull_request:
    branches: [main]

jobs:
  load-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

      redis:
        image: redis:7-alpine

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Start application
        run: |
          gunicorn app.main:create_app() --config gunicorn.conf.py &
          sleep 5

      - name: Install k6
        run: |
          curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz -L | tar xvz
          sudo mv k6-v0.47.0-linux-amd64/k6 /usr/local/bin/

      - name: Run load test
        run: |
          k6 run tests/load/k6-script.js

      - name: Check thresholds
        run: |
          # k6 exit code 99 = thresholds failed
          # This step fails the build if performance degrades
```

## Best Practices

### 1. Test Realistic Scenarios

```python
# ❌ Bad: Only test health checks
@task
def health():
    self.client.get("/health")

# ✅ Good: Test actual user workflows
@task
def user_workflow(self):
    # Login
    auth = self.client.post("/api/auth/login", ...)
    token = auth.json()["token"]

    # Browse products
    self.client.get("/api/products", headers={"Authorization": token})

    # Add to cart
    self.client.post("/api/cart/add", ...)

    # Checkout
    self.client.post("/api/checkout", ...)
```

### 2. Use Production-Like Data

```python
# Load production database snapshot
pg_restore -d test_db production_snapshot.dump

# Or generate realistic test data
python scripts/generate_test_data.py --users 100000 --products 10000
```

### 3. Monitor During Tests

```bash
# Terminal 1: Run load test
k6 run k6-script.js

# Terminal 2: Monitor system
watch -n 1 'docker stats'

# Terminal 3: Monitor database
watch -n 1 'psql -c "SELECT count(*) FROM pg_stat_activity"'

# Terminal 4: Monitor logs
docker-compose logs -f web
```

### 4. Establish Baselines

```bash
# Save results for comparison
k6 run k6-script.js --out json=baseline.json

# Later, compare
k6 run k6-script.js --out json=current.json
python scripts/compare_results.py baseline.json current.json
```

### 5. Test at Different Scales

```bash
# Small (50 users)
locust -f locustfile.py --users 50 --run-time 5m

# Medium (200 users)
locust -f locustfile.py --users 200 --run-time 10m

# Large (1000 users)
locust -f locustfile.py --users 1000 --run-time 30m
```

## Troubleshooting Poor Performance

### Symptom: High Latency

**Check**:
```python
# Add timing middleware
@app.middleware("http")
async def log_timing(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(f"{request.method} {request.url.path} took {duration:.3f}s")
    return response
```

**Common causes**:
- Slow database queries → Add indexes
- N+1 queries → Use joins or prefetch
- Blocking I/O → Use async
- No caching → Add Redis cache

### Symptom: Low Throughput

**Check**:
```bash
# Are workers saturated?
htop  # Check if all CPUs at 100%

# Is database the bottleneck?
pg_stat_statements  # Find slow queries

# Network issue?
iftop  # Check network utilization
```

**Common causes**:
- Too few workers → Increase workers
- Database connection pool exhausted → Increase pool size
- Synchronous code in async context → Fix with async/await

### Symptom: High Error Rate

**Check application logs**:
```bash
docker-compose logs web | grep ERROR

# Common errors:
# - "Connection refused" → Service down
# - "Too many connections" → Pool exhausted
# - "Timeout" → Slow operations
```

## Next Steps

1. **Run baseline tests** - Establish performance benchmarks
2. **Set performance budgets** - Define acceptable latency/throughput
3. **Automate testing** - Add to CI/CD pipeline
4. **Monitor production** - Compare test results to real traffic
5. **Iterate** - Test → Optimize → Repeat

Need help with specific performance issues? See [Troubleshooting Guide](troubleshooting.md).

## References

- [Locust Documentation](https://docs.locust.io/)
- [k6 Documentation](https://k6.io/docs/)
- [siege Manual](https://www.joedog.org/siege-manual/)
- [Performance Testing Best Practices](https://k6.io/docs/test-types/)
