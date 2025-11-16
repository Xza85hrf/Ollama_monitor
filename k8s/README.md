# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying Ollama Monitor in a Kubernetes cluster.

## Files

- `deployment.yaml` - Main deployment configuration
- `service.yaml` - Service to expose metrics
- `configmap.yaml` - Configuration for the monitor
- `servicemonitor.yaml` - Prometheus ServiceMonitor (requires Prometheus Operator)

## Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Ollama service running in the cluster

## Quick Start

### 1. Update Configuration

Edit `configmap.yaml` to configure your endpoints:

```yaml
base_url: "http://ollama-service:11434"
endpoints:
  "/":
    method: "GET"
    expected_status: 200
```

### 2. Deploy

Apply all manifests:

```bash
kubectl apply -f k8s/
```

Or deploy individually:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### 3. Verify

Check the deployment:

```bash
kubectl get pods -l app=ollama-monitor
kubectl logs -l app=ollama-monitor
```

### 4. Access Metrics

Port-forward to access metrics locally:

```bash
kubectl port-forward svc/ollama-monitor 8000:8000
curl http://localhost:8000/metrics
```

## Configuration

### Environment Variables

You can override configuration via environment variables in `deployment.yaml`:

```yaml
env:
- name: OLLAMA_API_BASE
  value: "http://ollama-service:11434"
- name: LOG_LEVEL
  value: "INFO"
- name: LOG_FORMAT
  value: "json"
```

### Alerting

To enable webhook alerting, update the `configmap.yaml`:

```yaml
alerting:
  enabled: true
  webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  alert_on_failure: true
  alert_threshold: 0.95
  min_failures: 3
```

## Prometheus Integration

### Option 1: Prometheus Operator

If using Prometheus Operator, apply the ServiceMonitor:

```bash
kubectl apply -f k8s/servicemonitor.yaml
```

### Option 2: Manual Prometheus Configuration

Add to your Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'ollama-monitor'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - default
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: ollama-monitor
```

## Security

The deployment follows security best practices:

- Runs as non-root user (UID 1000)
- Read-only root filesystem
- Drops all capabilities
- No privilege escalation
- Resource limits enforced

## Scaling

To scale the deployment:

```bash
kubectl scale deployment ollama-monitor --replicas=3
```

Note: Multiple replicas will all monitor independently.

## Troubleshooting

### Check logs

```bash
kubectl logs -l app=ollama-monitor -f
```

### Check configuration

```bash
kubectl get configmap ollama-monitor-config -o yaml
```

### Restart deployment

```bash
kubectl rollout restart deployment ollama-monitor
```

### Check connectivity to Ollama

```bash
kubectl exec -it deployment/ollama-monitor -- sh
# Inside the pod:
curl http://ollama-service:11434
```

## Cleanup

Remove all resources:

```bash
kubectl delete -f k8s/
```
