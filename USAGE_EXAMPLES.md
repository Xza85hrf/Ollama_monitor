# Usage Examples

This document provides practical examples of using Ollama Monitor with all its features.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Configuration](#configuration)
- [Report Formats](#report-formats)
- [Alerting](#alerting)
- [Monitoring Modes](#monitoring-modes)
- [Logging](#logging)
- [Advanced Examples](#advanced-examples)

## Basic Usage

### Simple Health Check

```bash
# Check default Ollama endpoint
python ollama_monitor.py --url http://localhost:11434

# Output: ollama_monitor_report.txt
```

### With Configuration File

```bash
# Use YAML configuration
python ollama_monitor.py --config config.yaml

# Validate configuration without running
python ollama_monitor.py --config config.yaml --validate-config
```

## Configuration

### Basic Configuration

Create `config.yaml`:

```yaml
base_url: "http://localhost:11434"
timeout: 30
endpoints:
  "/":
    path: "/"
    method: "GET"
    expected_status: 200
    expected_content: "Ollama is running"
```

### Advanced Configuration with Alerting

```yaml
base_url: "http://localhost:11434"
timeout: 30

endpoints:
  "/":
    path: "/"
    method: "GET"
    expected_status: 200
    expected_content: "Ollama is running"

  "/api/generate":
    path: "/api/generate"
    method: "POST"
    expected_status: 200
    headers:
      Content-Type: "application/json"
    body:
      model: "llama2"
      prompt: "Say hello"
      stream: false

  "/api/tags":
    path: "/api/tags"
    method: "GET"
    expected_status: 200

alerting:
  enabled: true
  webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  alert_on_failure: true
  alert_threshold: 0.95  # Alert if success rate < 95%
  min_failures: 3        # Alert after 3 consecutive failures
```

## Report Formats

### Text Report (Default)

```bash
python ollama_monitor.py --config config.yaml --format text
# Output: ollama_monitor_report.txt
```

**Output Example:**
```
Ollama Monitor Report
=====================
Generated: 2024-11-16T10:30:00Z

Endpoint 1:
  Status Code: 200
  Response Time: 0.12 seconds

Endpoint 2:
  Status Code: 200
  Response Time: 0.45 seconds
```

### JSON Report

```bash
python ollama_monitor.py --config config.yaml --format json
# Output: ollama_monitor_report.json
```

**Output Example:**
```json
{
  "timestamp": "2024-11-16T10:30:00Z",
  "summary": {
    "total_endpoints": 3,
    "successful": 2,
    "failed": 1
  },
  "endpoints": [
    {
      "name": "/",
      "status": "success",
      "status_code": 200,
      "response_time_seconds": 0.123
    },
    {
      "name": "/api/generate",
      "status": "success",
      "status_code": 200,
      "response_time_seconds": 0.456
    }
  ]
}
```

### CSV Report

```bash
python ollama_monitor.py --config config.yaml --format csv
# Output: ollama_monitor_report.csv
```

**Output Example:**
```csv
Endpoint,Status,Status Code,Response Time (s),Error
/,success,200,0.123,-
/api/generate,success,200,0.456,-
/api/tags,failed,500,-,Internal Server Error
```

### HTML Report

```bash
python ollama_monitor.py --config config.yaml --format html
# Output: ollama_monitor_report.html
```

Opens a beautiful HTML report with:
- Summary statistics
- Color-coded status indicators
- Responsive table layout
- Professional styling

### Custom Output Path

```bash
# Specify custom output filename
python ollama_monitor.py --config config.yaml --format json --output /tmp/my_report.json
```

## Alerting

### Slack Webhook Integration

1. Create a Slack webhook at https://api.slack.com/messaging/webhooks

2. Configure in `config.yaml`:

```yaml
alerting:
  enabled: true
  webhook_url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX"
  alert_on_failure: true
  alert_threshold: 0.95
  min_failures: 3
```

3. Run continuous monitoring:

```bash
python ollama_monitor.py --config config.yaml --continuous --interval 60
```

**Alert Example:**
```json
{
  "timestamp": "2024-11-16T10:30:00Z",
  "severity": "error",
  "message": "Endpoint '/api/generate' has failed 3 times consecutively",
  "service": "ollama-monitor",
  "endpoint": "/api/generate",
  "details": {
    "consecutive_failures": 3,
    "total_checks": 10,
    "last_error": "Status code: 500"
  }
}
```

### Custom Webhook Integration

Works with any webhook endpoint (Microsoft Teams, Discord, custom services):

```yaml
alerting:
  enabled: true
  webhook_url: "https://your-custom-endpoint.com/webhook"
  alert_on_failure: true
  alert_threshold: 0.90
  min_failures: 5
```

## Monitoring Modes

### One-Time Check

```bash
# Single check, generate report, and exit
python ollama_monitor.py --config config.yaml
```

### Load Testing

```bash
# Send 1000 requests with 50 concurrent connections
python ollama_monitor.py \
  --url http://localhost:11434 \
  --load-test \
  --num-requests 1000 \
  --concurrency 50
```

**Output:**
```
Load Test Results:
total_requests: 1000
concurrency: 50
successful_requests: 998
failed_requests: 2
average_response_time: 0.145
median_response_time: 0.132
p95_response_time: 0.287
min_response_time: 0.089
max_response_time: 1.234
```

### Continuous Monitoring

```bash
# Check every 60 seconds indefinitely
python ollama_monitor.py \
  --config config.yaml \
  --continuous \
  --interval 60
```

With Prometheus metrics:

```bash
python ollama_monitor.py \
  --config config.yaml \
  --continuous \
  --interval 30 \
  --prometheus
```

Access metrics at http://localhost:8000/metrics

## Logging

### Standard Text Logs

```bash
# Default logging
python ollama_monitor.py --config config.yaml

# Set log level
export LOG_LEVEL=DEBUG
python ollama_monitor.py --config config.yaml
```

**Output:**
```
2024-11-16 10:30:00 - __main__ - INFO - Ollama Monitor starting...
2024-11-16 10:30:01 - __main__ - INFO - Configuration validated successfully
2024-11-16 10:30:01 - __main__ - INFO - Testing URL: http://localhost:11434/
2024-11-16 10:30:01 - __main__ - INFO - Status: 200, Time: 0.12s
```

### JSON Structured Logs

```bash
# Enable JSON logging
python ollama_monitor.py --config config.yaml --json-logs

# Or via environment variable
export LOG_FORMAT=json
python ollama_monitor.py --config config.yaml
```

**Output:**
```json
{"timestamp":"2024-11-16T10:30:00Z","level":"INFO","logger":"__main__","message":"Ollama Monitor starting...","module":"ollama_monitor","function":"main","line":421}
{"timestamp":"2024-11-16T10:30:01Z","level":"INFO","logger":"__main__","message":"Testing URL: http://localhost:11434/","module":"ollama_monitor","function":"check_endpoint","line":152,"endpoint":"/"}
{"timestamp":"2024-11-16T10:30:01Z","level":"INFO","logger":"__main__","message":"Status: 200, Time: 0.12s","module":"ollama_monitor","function":"check_endpoint","line":168,"endpoint":"/","status_code":200,"response_time":0.123}
```

Perfect for log aggregation tools like:
- Elasticsearch + Kibana
- Splunk
- Datadog
- CloudWatch

## Advanced Examples

### Production Deployment with Docker

```bash
# Build image
docker build -t ollama-monitor .

# Run with volume-mounted config
docker run -d \
  --name ollama-monitor \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -e LOG_FORMAT=json \
  -e LOG_LEVEL=INFO \
  ollama-monitor:latest \
  python ollama_monitor.py \
    --config /app/config.yaml \
    --continuous \
    --interval 30 \
    --prometheus
```

### Docker Compose Stack

```bash
# Start full monitoring stack
docker-compose up -d

# View logs
docker-compose logs -f ollama-monitor

# Access services
# - Ollama Monitor metrics: http://localhost:8000/metrics
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

### Kubernetes Deployment

```bash
# Update configuration
kubectl edit configmap ollama-monitor-config

# Deploy
kubectl apply -f k8s/

# Check logs
kubectl logs -l app=ollama-monitor -f

# Port-forward for metrics
kubectl port-forward svc/ollama-monitor 8000:8000
```

### Automated Testing in CI/CD

```bash
#!/bin/bash
# ci-health-check.sh

# Run health check
python ollama_monitor.py \
  --config config.yaml \
  --format json \
  --output health-check.json

# Parse results
SUCCESS=$(jq '.summary.successful' health-check.json)
TOTAL=$(jq '.summary.total_endpoints' health-check.json)

if [ "$SUCCESS" -eq "$TOTAL" ]; then
  echo "✓ All endpoints healthy"
  exit 0
else
  echo "✗ Some endpoints failed"
  cat health-check.json
  exit 1
fi
```

### Monitoring Multiple Ollama Instances

```yaml
# config-prod.yaml
base_url: "http://ollama-prod:11434"
timeout: 30
endpoints:
  "/": { path: "/", method: "GET", expected_status: 200 }

# config-staging.yaml
base_url: "http://ollama-staging:11434"
timeout: 30
endpoints:
  "/": { path: "/", method: "GET", expected_status: 200 }
```

```bash
# Monitor both environments
python ollama_monitor.py --config config-prod.yaml --format json --output prod-report.json &
python ollama_monitor.py --config config-staging.yaml --format json --output staging-report.json &
wait
```

### Performance Baseline Testing

```bash
# Run load test to establish baseline
python ollama_monitor.py \
  --url http://localhost:11434 \
  --load-test \
  --num-requests 10000 \
  --concurrency 100 \
  > baseline-results.txt

# Extract p95 latency
grep "p95_response_time" baseline-results.txt

# Use in monitoring
# Set alert threshold based on baseline + margin
```

### Health Check with Exit Codes

```bash
# Run check and capture exit code
python ollama_monitor.py --config config.yaml --format json --output check.json

# Use in scripts
if [ $? -eq 0 ]; then
  echo "Monitoring completed successfully"
else
  echo "Monitoring encountered errors"
  exit 1
fi
```

### Debug Mode

```bash
# Maximum verbosity
export LOG_LEVEL=DEBUG
python ollama_monitor.py --config config.yaml --json-logs

# View full HTTP responses
# See retry attempts
# Track timing details
```

## Environment Variables

All available environment variables:

```bash
# Ollama server URL
export OLLAMA_API_BASE=http://localhost:11434

# Request timeout
export DEFAULT_TIMEOUT=30

# Retry configuration
export RETRY_ATTEMPTS=5
export RETRY_DELAY=3

# Logging
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
export LOG_FORMAT=json  # json or text
```

## Troubleshooting

### Configuration Validation Errors

```bash
# Validate your config first
python ollama_monitor.py --config config.yaml --validate-config

# Common errors:
# - Invalid URL format
# - Invalid HTTP method
# - Missing required fields
```

### Connection Issues

```bash
# Test connectivity
curl http://localhost:11434/

# Check Ollama is running
docker ps | grep ollama

# Verify network access
ping ollama-server
```

### Alert Not Firing

```bash
# Check alert configuration
python ollama_monitor.py --config config.yaml --validate-config

# Test webhook manually
curl -X POST https://your-webhook-url \
  -H "Content-Type: application/json" \
  -d '{"text": "Test alert"}'

# Check logs for alert attempts
export LOG_LEVEL=DEBUG
python ollama_monitor.py --config config.yaml --continuous --json-logs
```

## Best Practices

1. **Always validate configuration** before deploying
2. **Use JSON logs** in production for better parsing
3. **Set appropriate alert thresholds** based on your SLOs
4. **Monitor the monitor** - collect metrics from Prometheus
5. **Use version control** for configuration files
6. **Test webhooks** before relying on alerts
7. **Set resource limits** in production (Docker/K8s)
8. **Rotate logs** if running continuously
9. **Use HTTPS** for production Ollama endpoints
10. **Keep configs DRY** - use YAML anchors for repeated sections

## Additional Resources

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Kubernetes Deployment](k8s/README.md)
- [Changelog](CHANGELOG.md)
