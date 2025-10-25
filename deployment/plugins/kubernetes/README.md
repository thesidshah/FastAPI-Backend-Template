# Kubernetes Deployment Plugin

**Level 4 Scaling**: Deploy FastAPI backend to Kubernetes with auto-scaling and production-grade reliability.

## Overview

This plugin provides CLI tools and manifest templates for deploying the FastAPI backend to Kubernetes clusters. It handles:

- Multi-replica deployments with auto-scaling
- Rolling updates and rollbacks
- Health checks and readiness probes
- ConfigMaps and Secrets management
- Service and Ingress configuration
- Horizontal Pod Autoscaling (HPA)

## Installation

```bash
# Install Kubernetes plugin
pip install -e ".[k8s]"
```

This installs:
- `kubernetes` Python client
- `pyyaml` for manifest templating
- CLI tools in `deployment.plugins.kubernetes`

## Prerequisites

- Kubernetes cluster (1.20+)
- `kubectl` configured and connected
- Container registry access
- (Optional) `metrics-server` for HPA

## Quick Start

### 1. Build and Push Image

```bash
# Build image
docker build -t your-registry.com/fastapi-backend:v1.0 .

# Push to registry
docker push your-registry.com/fastapi-backend:v1.0
```

### 2. Deploy to Kubernetes

```bash
# Deploy with default settings
python -m deployment.plugins.kubernetes deploy \
  --namespace production \
  --image your-registry.com/fastapi-backend:v1.0 \
  --replicas 3

# Or use kubectl directly with manifests
kubectl apply -f deployment/plugins/kubernetes/manifests/
```

### 3. Verify Deployment

```bash
# Check status
python -m deployment.plugins.kubernetes status

# Or use kubectl
kubectl get deployments,pods,services -n production
```

## CLI Commands

### Deploy

Deploy or update the application:

```bash
python -m deployment.plugins.kubernetes deploy [OPTIONS]

Options:
  --namespace TEXT     Kubernetes namespace [default: default]
  --image TEXT         Container image with tag [required]
  --replicas INTEGER   Initial replica count [default: 3]
  --config FILE        Custom configuration file
  --dry-run           Show what would be deployed
```

Example:
```bash
python -m deployment.plugins.kubernetes deploy \
  --namespace production \
  --image registry.example.com/fastapi:v2.0 \
  --replicas 5
```

### Scale

Scale the deployment up or down:

```bash
python -m deployment.plugins.kubernetes scale --replicas INTEGER

Options:
  --namespace TEXT     Kubernetes namespace
  --replicas INTEGER   Desired replica count [required]
```

Example:
```bash
# Scale to 10 replicas
python -m deployment.plugins.kubernetes scale --replicas 10
```

### Rollback

Rollback to previous deployment:

```bash
python -m deployment.plugins.kubernetes rollback [OPTIONS]

Options:
  --namespace TEXT     Kubernetes namespace
  --revision INTEGER   Specific revision to rollback to
```

Example:
```bash
# Rollback to previous version
python -m deployment.plugins.kubernetes rollback

# Rollback to specific revision
python -m deployment.plugins.kubernetes rollback --revision 3
```

### Status

Get deployment status and health:

```bash
python -m deployment.plugins.kubernetes status [OPTIONS]

Options:
  --namespace TEXT     Kubernetes namespace
  --watch             Watch for changes
```

Example:
```bash
# Get current status
python -m deployment.plugins.kubernetes status

# Watch for updates
python -m deployment.plugins.kubernetes status --watch
```

## Manifest Files

Located in `deployment/plugins/kubernetes/manifests/`:

### deployment.yaml

Core application deployment with:
- Multi-container pods
- Resource limits (CPU, memory)
- Liveness and readiness probes
- Environment variables from ConfigMaps/Secrets
- Rolling update strategy

### service.yaml

Kubernetes Service for internal communication:
- ClusterIP service type
- Port mapping (80 → 8000)
- Selector matching deployment pods

### hpa.yaml

Horizontal Pod Autoscaler:
- Auto-scales based on CPU/memory
- Min replicas: 3
- Max replicas: 20
- Target CPU: 70%
- Target Memory: 80%

### configmap.yaml

Application configuration:
- Environment-specific settings
- Feature flags
- Non-sensitive configuration

### ingress.yaml

External access configuration:
- TLS termination
- Domain routing
- Path-based routing
- Rate limiting annotations

## Configuration

### Environment Variables

Set via ConfigMap or Secrets:

```yaml
# configmap.yaml
data:
  APP_ENVIRONMENT: "production"
  APP_LOG_LEVEL: "INFO"
  WORKERS: "4"

# secrets.yaml (base64 encoded)
data:
  JWT_SECRET: "<base64-encoded-secret>"
  DATABASE_URL: "<base64-encoded-url>"
```

Create secrets:
```bash
kubectl create secret generic fastapi-secrets \
  --from-literal=JWT_SECRET=$(openssl rand -hex 32) \
  --from-literal=DATABASE_URL="postgresql://..." \
  -n production
```

### Resource Limits

Adjust in `deployment.yaml`:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### Auto-Scaling

Modify `hpa.yaml`:

```yaml
minReplicas: 3
maxReplicas: 20
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70
```

## Production Best Practices

### 1. Use Namespaces

Separate environments:
```bash
kubectl create namespace production
kubectl create namespace staging
```

### 2. Configure Resource Limits

Always set requests and limits to prevent resource exhaustion.

### 3. Enable Auto-Scaling

Use HPA for automatic scaling based on metrics:
```bash
kubectl autoscale deployment fastapi-backend \
  --cpu-percent=70 \
  --min=3 \
  --max=20 \
  -n production
```

### 4. Set Up Monitoring

- Install metrics-server
- Configure Prometheus for metrics
- Set up alerting rules

### 5. Use Rolling Updates

Ensure zero-downtime deployments:
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

### 6. Configure Health Checks

Properly configure liveness and readiness:
```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /api/v1/health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n production

# View pod logs
kubectl logs -f <pod-name> -n production

# Describe pod for events
kubectl describe pod <pod-name> -n production
```

Common issues:
- Image pull errors (check registry credentials)
- Resource limits too low
- Health checks failing
- Missing ConfigMaps/Secrets

### Service Not Accessible

```bash
# Check service endpoints
kubectl get endpoints -n production

# Test service internally
kubectl run -it --rm debug --image=alpine --restart=Never -n production -- sh
# Inside pod:
wget -O- http://fastapi-backend/api/v1/health
```

### Auto-Scaling Not Working

```bash
# Check HPA status
kubectl get hpa -n production
kubectl describe hpa fastapi-backend-hpa -n production

# Verify metrics-server
kubectl top pods -n production
kubectl top nodes
```

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Production Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

## Support

For issues specific to this plugin:
- Check [Troubleshooting Guide](../../scaling/troubleshooting.md)
- Review [Level 4 Scaling Documentation](../../scaling/level4-horizontal-scaling.md)
- File issues on GitHub repository
