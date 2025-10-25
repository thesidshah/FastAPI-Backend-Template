# Docker Swarm Deployment Plugin

**Level 4 Scaling**: Deploy FastAPI backend to Docker Swarm with native container orchestration.

## Overview

This plugin provides CLI tools and stack files for deploying the FastAPI backend to Docker Swarm. It offers:

- Multi-replica services with automatic load balancing
- Rolling updates and rollback capabilities
- Health checks and restart policies
- Secrets and config management
- Service discovery and networking
- Stack-based deployment

## Installation

```bash
# Install Docker Swarm plugin
pip install -e ".[swarm]"
```

This installs:
- `docker` Python SDK
- CLI tools in `deployment.plugins.swarm`

## Prerequisites

- Docker 20.10+ with Swarm mode enabled
- Swarm cluster initialized
- (Optional) Docker registry for multi-node deployments

## Quick Start

### 1. Initialize Swarm

```bash
# On manager node
docker swarm init

# On worker nodes (use token from init output)
docker swarm join --token <token> <manager-ip>:2377

# Verify cluster
docker node ls
```

### 2. Build and Tag Image

```bash
# Build image
docker build -t fastapi-backend:latest .

# For multi-node: push to registry
docker tag fastapi-backend:latest registry.example.com/fastapi-backend:latest
docker push registry.example.com/fastapi-backend:latest
```

### 3. Deploy Stack

```bash
# Using CLI plugin
python -m deployment.plugins.swarm deploy \
  --stack-name myapp \
  --replicas 5

# Or using docker stack directly
docker stack deploy -c deployment/plugins/swarm/docker-swarm.yml myapp
```

### 4. Verify Deployment

```bash
# Check status
python -m deployment.plugins.swarm status --stack-name myapp

# Or use docker commands
docker stack services myapp
docker service ps myapp_api
```

## CLI Commands

### Deploy

Deploy or update a stack:

```bash
python -m deployment.plugins.swarm deploy [OPTIONS]

Options:
  --stack-name TEXT    Name for the stack [default: fastapi-backend]
  --replicas INTEGER   Number of replicas [default: 3]
  --config FILE        Custom stack file
  --env-file FILE      Environment variables file
```

Example:
```bash
python -m deployment.plugins.swarm deploy \
  --stack-name production \
  --replicas 10 \
  --env-file .env.production
```

### Scale

Scale services up or down:

```bash
python -m deployment.plugins.swarm scale [OPTIONS]

Options:
  --stack-name TEXT    Stack name
  --service TEXT       Service name [default: api]
  --replicas INTEGER   Desired replica count [required]
```

Example:
```bash
# Scale API service to 15 replicas
python -m deployment.plugins.swarm scale \
  --stack-name production \
  --replicas 15
```

### Rollback

Rollback to previous service version:

```bash
python -m deployment.plugins.swarm rollback [OPTIONS]

Options:
  --stack-name TEXT    Stack name
  --service TEXT       Service name to rollback
```

Example:
```bash
# Rollback API service
python -m deployment.plugins.swarm rollback \
  --stack-name production \
  --service api
```

### Status

Get stack and service status:

```bash
python -m deployment.plugins.swarm status [OPTIONS]

Options:
  --stack-name TEXT    Stack name
  --follow            Follow log output
```

Example:
```bash
# Get status
python -m deployment.plugins.swarm status --stack-name production

# Follow logs
python -m deployment.plugins.swarm status --stack-name production --follow
```

## Stack Files

### docker-swarm.yml

Main stack definition with:

```yaml
version: '3.8'

services:
  api:
    image: fastapi-backend:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      restart_policy:
        condition: on-failure
        max_attempts: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    ports:
      - "8000:8000"
    networks:
      - backend
    environment:
      - APP_ENVIRONMENT=production
    secrets:
      - jwt_secret
    configs:
      - source: app_config
        target: /app/config.yaml

  worker:
    image: fastapi-backend:latest
    command: rq worker default high priority
    deploy:
      replicas: 5
    networks:
      - backend

networks:
  backend:
    driver: overlay

secrets:
  jwt_secret:
    external: true

configs:
  app_config:
    external: true
```

## Configuration

### Secrets Management

Create and use secrets:

```bash
# Create secret
echo "my-secret-key" | docker secret create jwt_secret -

# Or from file
docker secret create db_password ./db_password.txt

# List secrets
docker secret ls

# Remove secret
docker secret rm jwt_secret
```

Reference in stack file:
```yaml
services:
  api:
    secrets:
      - jwt_secret
      - db_password
```

Access in app: `/run/secrets/jwt_secret`

### Configs

Create and use configs:

```bash
# Create config from file
docker config create app_config ./config.yaml

# Update config (create new version)
docker config create app_config_v2 ./config.yaml

# List configs
docker config ls
```

### Placement Constraints

Control where services run:

```yaml
deploy:
  placement:
    constraints:
      - node.role == worker
      - node.labels.type == compute
    preferences:
      - spread: node.labels.zone
```

### Update Configuration

Zero-downtime updates:

```yaml
deploy:
  update_config:
    parallelism: 2        # Update 2 at a time
    delay: 10s           # Wait 10s between batches
    failure_action: rollback
    monitor: 30s
    order: start-first   # Start new before stopping old
```

## Production Best Practices

### 1. Use Overlay Networks

Ensure services can communicate across nodes:
```bash
docker network create --driver overlay --attachable backend
```

### 2. Configure Resource Limits

Always set limits to prevent resource exhaustion:
```yaml
resources:
  limits:
    cpus: '2'
    memory: 2G
  reservations:
    cpus: '1'
    memory: 1G
```

### 3. Use Secrets for Sensitive Data

Never put secrets in environment variables:
```bash
# Good: Use Docker secrets
docker secret create jwt_secret <(openssl rand -hex 32)

# Bad: Plain environment variables
environment:
  - JWT_SECRET=my-secret-key  # ❌ Don't do this
```

### 4. Enable Health Checks

Configure service health checks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/ready"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 5. Use Rolling Updates

Ensure zero-downtime deployments:
```yaml
deploy:
  update_config:
    order: start-first
    failure_action: rollback
```

### 6. Implement Logging

Send logs to centralized system:
```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

## Scaling Strategies

### Manual Scaling

```bash
# Scale specific service
docker service scale myapp_api=10

# Scale multiple services
docker service scale myapp_api=10 myapp_worker=20
```

### Global Mode

Run one replica per node:
```yaml
deploy:
  mode: global
```

### Replicated Mode

Run specific number of replicas (default):
```yaml
deploy:
  mode: replicated
  replicas: 5
```

## Monitoring

### Service Status

```bash
# List services
docker service ls

# Inspect service
docker service inspect myapp_api

# View service logs
docker service logs -f myapp_api

# See running tasks
docker service ps myapp_api
```

### Node Management

```bash
# List nodes
docker node ls

# Inspect node
docker node inspect <node-id>

# Update node availability
docker node update --availability drain <node-id>
```

## Troubleshooting

### Services Not Starting

```bash
# Check service status
docker service ps myapp_api --no-trunc

# View logs
docker service logs myapp_api

# Inspect service
docker service inspect myapp_api
```

Common issues:
- Image not available on worker nodes (push to registry)
- Port conflicts
- Resource constraints
- Missing secrets/configs

### Network Issues

```bash
# List networks
docker network ls

# Inspect network
docker network inspect backend

# Test connectivity
docker run --rm --network backend alpine ping api
```

### Update Failures

```bash
# View update status
docker service inspect --pretty myapp_api

# Rollback if needed
docker service rollback myapp_api
```

## Cleanup

```bash
# Remove stack
docker stack rm myapp

# Remove secrets
docker secret rm jwt_secret db_password

# Remove configs
docker config rm app_config

# Leave swarm (worker nodes)
docker swarm leave

# Force remove swarm (manager)
docker swarm leave --force
```

## Additional Resources

- [Docker Swarm Documentation](https://docs.docker.com/engine/swarm/)
- [Stack File Reference](https://docs.docker.com/compose/compose-file/)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [Service Configuration](https://docs.docker.com/engine/swarm/services/)

## Support

For issues specific to this plugin:
- Check [Troubleshooting Guide](../../scaling/troubleshooting.md)
- Review [Level 4 Scaling Documentation](../../scaling/level4-horizontal-scaling.md)
- File issues on GitHub repository
