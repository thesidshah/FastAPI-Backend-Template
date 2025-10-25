# Level 4: Horizontal Scaling

**Complexity**: ⭐⭐⭐⭐ (Infrastructure setup, orchestration plugins)
**Performance**: 100K+ requests/second across multiple nodes
**When to use**: Single-machine capacity is exhausted or you need high availability

## Overview

Level 4 introduces **horizontal scaling**: distributing your application across multiple servers (nodes) behind a load balancer. This is the final scaling level, enabling true high availability and virtually unlimited capacity by adding more machines.

While Levels 1-3 scale **vertically** (more workers on one machine), Level 4 scales **horizontally** (more machines). This provides:
- **Higher capacity**: Add nodes to handle more traffic
- **High availability**: If one node fails, others continue serving traffic
- **Geographic distribution**: Deploy nodes in multiple regions
- **Rolling deployments**: Update nodes one at a time with zero downtime

## The Horizontal Scaling Paradigm Shift

**Level 3 (Single Server)**:
```
┌───────────────────────────────┐
│      Server (8 cores)         │
│  ┌─────────────────────────┐  │
│  │  Gunicorn + 4 Workers   │  │
│  └─────────────────────────┘  │
│                               │
│  Max: ~50K req/sec            │
└───────────────────────────────┘
```

**Level 4 (Multi-Server)**:
```
                    ┌──────────────────────┐
                    │   Load Balancer      │
                    │   (nginx/Traefik)    │
                    └──────┬───────────────┘
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
          ▼                ▼                 ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ Node 1  │      │ Node 2  │      │ Node 3  │
    │ 50K r/s │      │ 50K r/s │      │ 50K r/s │
    └─────────┘      └─────────┘      └─────────┘

    Combined: ~150K req/sec + High Availability
```

## Architecture

```
                            Internet
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Load Balancer      │
                    │   • nginx/Traefik    │
                    │   • Health checks    │
                    │   • SSL termination  │
                    └──────┬───────────────┘
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
          ▼                ▼                 ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │  Node 1   │    │  Node 2   │    │  Node 3   │
    │  FastAPI  │    │  FastAPI  │    │  FastAPI  │
    │  Gunicorn │    │  Gunicorn │    │  Gunicorn │
    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
          │                │                 │
          └────────────────┼─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Shared State   │
                  │  • Redis        │
                  │  • PostgreSQL   │
                  └─────────────────┘
```

## Key Concepts

### Load Balancer

Distributes incoming traffic across multiple nodes using various algorithms:

**Round Robin**: Requests sent to each node in sequence
- Node 1 → Node 2 → Node 3 → Node 1 → ...
- Simple, works well for stateless applications

**Least Connections**: New requests sent to node with fewest active connections
- Better for long-lived connections or varying request durations

**IP Hash / Session Affinity**: Same client always sent to same node
- Needed for sticky sessions or stateful applications
- Can cause uneven load distribution

### Health Checks

Load balancer regularly checks if nodes are healthy:

```python
# Health check endpoint
@app.get("/health/ready")
async def readiness_check():
    """Kubernetes-style readiness probe."""
    # Check database
    try:
        await db.execute("SELECT 1")
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")

    # Check Redis
    try:
        await redis.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    return {"status": "ready"}
```

Load balancer configuration:
```nginx
upstream backend {
    server node1:8000 max_fails=3 fail_timeout=30s;
    server node2:8000 max_fails=3 fail_timeout=30s;
    server node3:8000 max_fails=3 fail_timeout=30s;
}

# Health check every 5 seconds
location /health/ready {
    access_log off;
}
```

### Shared State

All nodes must share:
- **Database**: PostgreSQL (already centralized)
- **Cache**: Redis (already centralized)
- **Sessions**: Redis-backed sessions
- **File storage**: S3 or shared volume (not local disk)

**Critical**: Never store state locally on nodes. Everything must be in shared storage.

## Setup Options

Level 4 provides three deployment options:

### Option 1: Manual Load Balancer (nginx)

**Use when**: You have VMs or bare metal servers

Setup:
1. Deploy nginx as load balancer
2. Run application on multiple servers
3. Configure nginx to distribute traffic

**Pros**: Full control, simple to understand
**Cons**: Manual scaling, no auto-recovery

### Option 2: Docker Swarm Plugin

**Use when**: You want simple orchestration without K8s complexity

Setup:
```bash
pip install -e ".[swarm]"
python -m deployment.plugins.swarm deploy --stack-name myapp
```

**Pros**: Simpler than K8s, built into Docker
**Cons**: Less ecosystem, fewer features

### Option 3: Kubernetes Plugin

**Use when**: You need enterprise-grade orchestration

Setup:
```bash
pip install -e ".[k8s]"
python -m deployment.plugins.kubernetes deploy --namespace production
```

**Pros**: Industry standard, rich ecosystem, auto-scaling
**Cons**: Steeper learning curve, more complex

## Option 1: nginx Load Balancer

### Install nginx

```bash
# Ubuntu/Debian
apt-get install nginx

# macOS
brew install nginx

# Or use Docker
docker run -d -p 80:80 nginx:alpine
```

### Configure nginx

Create `deployment/nginx.conf`:

```nginx
# upstream backend servers
upstream fastapi_backend {
    # Load balancing algorithm
    least_conn;  # Or: round_robin, ip_hash

    # Backend servers
    server node1.example.com:8000 max_fails=3 fail_timeout=30s;
    server node2.example.com:8000 max_fails=3 fail_timeout=30s;
    server node3.example.com:8000 max_fails=3 fail_timeout=30s;

    # Health check interval
    keepalive 32;
}

server {
    listen 80;
    server_name api.example.com;

    # Access logging
    access_log /var/log/nginx/api_access.log;
    error_log /var/log/nginx/api_error.log;

    # Client limits
    client_max_body_size 10M;
    client_body_timeout 60s;

    # Proxy settings
    location / {
        proxy_pass http://fastapi_backend;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check endpoint (no logging)
    location /health {
        proxy_pass http://fastapi_backend;
        access_log off;
    }

    # Websocket support (if needed)
    location /ws {
        proxy_pass http://fastapi_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# HTTPS (production)
server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL certificates
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Same proxy configuration as port 80
    location / {
        proxy_pass http://fastapi_backend;
        # ... (same as above)
    }
}
```

### Deploy Application Nodes

On each server (node1, node2, node3):

```bash
# Pull latest code
git pull

# Build and run with Docker
docker-compose -f deployment/docker-compose.prod.yml up -d

# Or run directly
gunicorn app.main:create_app() --config gunicorn.conf.py --bind 0.0.0.0:8000
```

### Test Load Balancer

```bash
# Check nginx config
nginx -t

# Reload nginx
nginx -s reload

# Test distribution
for i in {1..10}; do
  curl http://api.example.com/health/worker
done

# Should see different worker_ids across nodes
```

## Option 2: Docker Swarm Plugin

### Install Plugin

```bash
pip install -e ".[swarm]"
```

This installs:
- `docker>=7.1.0` - Docker SDK

### Initialize Swarm

```bash
# On manager node
docker swarm init --advertise-addr <MANAGER-IP>

# On worker nodes (copy token from init output)
docker swarm join --token <TOKEN> <MANAGER-IP>:2377
```

### Deploy with Plugin

```bash
# Deploy stack
python -m deployment.plugins.swarm deploy \
  --stack-name production-api \
  --replicas 3 \
  --image your-registry.com/fastapi-backend:latest

# Scale service
python -m deployment.plugins.swarm scale \
  --service web \
  --replicas 5

# Check status
python -m deployment.plugins.swarm status

# Rollback deployment
python -m deployment.plugins.swarm rollback
```

### Swarm Stack File

`deployment/plugins/swarm/docker-swarm.yml`:

```yaml
version: '3.8'

services:
  web:
    image: your-registry.com/fastapi-backend:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first  # Zero downtime
      rollback_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - WORKERS=4
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    networks:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == manager  # DB on manager only
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    volumes:
      - db_data:/var/lib/postgresql/data
    networks:
      - backend
    secrets:
      - db_password

  redis:
    image: redis:7-alpine
    deploy:
      replicas: 1
    volumes:
      - redis_data:/data
    networks:
      - backend

volumes:
  db_data:
  redis_data:

networks:
  backend:
    driver: overlay

secrets:
  db_password:
    external: true
```

Deploy:
```bash
docker stack deploy -c deployment/plugins/swarm/docker-swarm.yml production-api
```

## Option 3: Kubernetes Plugin

### Install Plugin

```bash
pip install -e ".[k8s]"
```

This installs:
- `kubernetes>=30.1.0` - K8s Python client
- `pyyaml>=6.0.2` - YAML parsing

### Deploy with Plugin

```bash
# Deploy to cluster
python -m deployment.plugins.kubernetes deploy \
  --namespace production \
  --image your-registry.com/fastapi-backend:latest \
  --replicas 3

# Scale deployment
python -m deployment.plugins.kubernetes scale \
  --replicas 5

# Check status
python -m deployment.plugins.kubernetes status

# Rollback to previous version
python -m deployment.plugins.kubernetes rollback
```

### Kubernetes Manifests

`deployment/plugins/kubernetes/manifests/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-backend
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero downtime
  selector:
    matchLabels:
      app: fastapi-backend
  template:
    metadata:
      labels:
        app: fastapi-backend
    spec:
      containers:
      - name: web
        image: your-registry.com/fastapi-backend:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: WORKERS
          value: "4"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

`deployment/plugins/kubernetes/manifests/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi-backend
  namespace: production
spec:
  type: LoadBalancer
  selector:
    app: fastapi-backend
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
```

`deployment/plugins/kubernetes/manifests/hpa.yaml` (Horizontal Pod Autoscaler):

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-backend-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Deploy manually:
```bash
kubectl apply -f deployment/plugins/kubernetes/manifests/
```

## Shared State Configuration

### Session Affinity (Sticky Sessions)

**When needed**: Stateful applications that store session in memory

**nginx**:
```nginx
upstream backend {
    ip_hash;  # Same client IP always goes to same server
    server node1:8000;
    server node2:8000;
}
```

**Kubernetes**:
```yaml
apiVersion: v1
kind: Service
spec:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800  # 3 hours
```

**Better approach**: Use Redis for sessions (no affinity needed)

```python
# config.py
SESSION_TYPE = "redis"
SESSION_REDIS = redis.from_url(os.getenv("REDIS_URL"))
```

### Distributed Caching

All nodes share Redis for caching:

```python
# app/core/cache.py
import redis.asyncio as aioredis

redis_client = aioredis.from_url(
    os.getenv("SHARED_CACHE_URL", "redis://redis:6379/3"),
    decode_responses=True
)

async def get_cached(key: str):
    return await redis_client.get(key)

async def set_cached(key: str, value: str, ttl: int = 3600):
    await redis_client.set(key, value, ex=ttl)
```

### File Storage

**Never use local disk** for file uploads/storage across multiple nodes.

**Options**:
1. **S3 / Object Storage** (recommended)
2. **Shared Network Volume** (NFS, EFS)
3. **Database BLOB fields** (small files only)

```python
# Use S3 for file storage
import boto3

s3 = boto3.client('s3')

@app.post("/upload")
async def upload_file(file: UploadFile):
    s3.upload_fileobj(
        file.file,
        bucket="my-app-uploads",
        key=f"uploads/{file.filename}"
    )
    return {"url": f"s3://my-app-uploads/uploads/{file.filename}"}
```

## Monitoring Multi-Node Deployments

### Centralized Logging

All nodes send logs to central location:

**Option 1: ELK Stack** (Elasticsearch + Logstash + Kibana)
**Option 2: Grafana Loki**
**Option 3: Cloud provider logging** (CloudWatch, Stackdriver)

```python
# Configure JSON logging for parsing
import logging
import json_log_formatter

formatter = json_log_formatter.JSONFormatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)

# Each log includes node info
logger.info("Request processed", extra={
    "node_id": os.getenv("NODE_ID"),
    "worker_id": os.getpid(),
    "request_id": request_id
})
```

### Distributed Tracing

Track requests across multiple nodes:

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracing
FastAPIInstrumentor.instrument_app(app)

# Traces show full request path:
# nginx → node2 → database → redis → node2 → nginx
```

### Health Dashboard

Monitor all nodes from single dashboard:

```python
@app.get("/health/cluster")
async def cluster_health(redis: Redis = Depends()):
    # Each node registers heartbeat in Redis
    await redis.setex(
        f"node:{os.getenv('NODE_ID')}:heartbeat",
        30,  # 30 second TTL
        json.dumps({
            "node_id": os.getenv("NODE_ID"),
            "workers": 4,
            "uptime": time.time() - START_TIME
        })
    )

    # Get all nodes
    nodes = []
    for key in await redis.keys("node:*:heartbeat"):
        node_data = await redis.get(key)
        nodes.append(json.loads(node_data))

    return {
        "total_nodes": len(nodes),
        "healthy_nodes": len(nodes),
        "nodes": nodes
    }
```

## Best Practices

### 1. Design for Statelessness

```python
# ❌ Bad: Node-local state
user_sessions = {}  # Lost when node restarts

# ✅ Good: Shared state
user_sessions = RedisDict(redis_url)
```

### 2. Use Health Checks

```python
@app.get("/health/ready")
async def readiness():
    # Check all dependencies
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "external_api": await check_external_api()
    }

    if not all(checks.values()):
        raise HTTPException(status_code=503, detail=checks)

    return {"status": "ready", "checks": checks}
```

### 3. Implement Graceful Shutdown

```python
# Handle SIGTERM for graceful shutdown
import signal

def shutdown_handler(signum, frame):
    logger.info("Graceful shutdown initiated")
    # Close database connections
    # Finish in-flight requests
    # Deregister from load balancer
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
```

### 4. Use Rolling Deployments

**Kubernetes** (automatic):
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0  # Zero downtime
```

**Docker Swarm**:
```yaml
deploy:
  update_config:
    parallelism: 1  # Update 1 at a time
    delay: 10s
    order: start-first  # Start new before stopping old
```

### 5. Monitor Node Distribution

```bash
# Check request distribution across nodes
for i in {1..100}; do
  curl -s http://api.example.com/health/worker | jq -r .node_id
done | sort | uniq -c

# Should show roughly equal distribution:
#  33 node1
#  34 node2
#  33 node3
```

## Troubleshooting

### Issue 1: Uneven Load Distribution

**Symptoms**: One node handles most traffic

**Causes**:
- Session affinity enabled
- Long-lived connections to one node
- Incorrect load balancer algorithm

**Solutions**:
```nginx
# Use least_conn instead of ip_hash
upstream backend {
    least_conn;  # Not ip_hash
    server node1:8000;
    server node2:8000;
}
```

### Issue 2: Nodes Out of Sync

**Symptoms**: Inconsistent data across nodes

**Causes**:
- Local caching without invalidation
- Using node-local storage

**Solutions**:
```python
# Use Redis for caching
@lru_cache  # ❌ Bad: local cache
def get_config():
    pass

# ✅ Good: Shared Redis cache
async def get_config():
    return await redis.get("config")
```

### Issue 3: Database Connection Exhaustion

**Symptoms**: "Too many connections" with multiple nodes

**Causes**:
- Each node creates full connection pool
- `pool_size × nodes × workers` exceeds database max

**Solutions**:
```python
# Reduce pool size per node
pool_size = max(5, 100 // (num_nodes * workers_per_node))
```

## Performance Expectations

**3-node cluster** (each node: 8 cores, 4 workers):
- Combined capacity: ~150K req/sec
- High availability: 2 nodes can handle full load
- Rolling deployments: Zero downtime updates

**Scaling efficiency**:
- 1 node: 50K req/sec (baseline)
- 2 nodes: 95K req/sec (95% efficiency)
- 3 nodes: 140K req/sec (93% efficiency)
- 5 nodes: 225K req/sec (90% efficiency)

**Why not 100% scaling**:
- Shared database bottleneck
- Network latency between nodes
- Load balancer overhead

## When You've Mastered Level 4

At this point, you have:
- ✅ Multi-node deployment
- ✅ Load balancing
- ✅ High availability
- ✅ Auto-scaling (K8s/Swarm)
- ✅ Zero-downtime deployments
- ✅ 100K+ req/sec capacity

**Further optimizations**:
- **Database read replicas** - Distribute read load
- **CDN** - Cache static assets and API responses
- **Geographic distribution** - Multi-region deployments
- **Edge computing** - Process requests closer to users

## Next Steps

1. **Choose deployment option** - nginx, Swarm, or K8s
2. **Configure load balancer** - Health checks, SSL, logging
3. **Deploy to multiple nodes** - Start with 2-3 nodes
4. **Test failover** - Kill a node, verify traffic continues
5. **Monitor distribution** - Ensure even load across nodes

Need help with performance testing? See [Load Testing Guide](load-testing.md).

Encountering issues? Check [Troubleshooting Guide](troubleshooting.md).

## References

- [nginx Load Balancing](https://nginx.org/en/docs/http/load_balancing.html)
- [Docker Swarm Documentation](https://docs.docker.com/engine/swarm/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes Plugin README](../../deployment/plugins/kubernetes/README.md)
- [Docker Swarm Plugin README](../../deployment/plugins/swarm/README.md)
