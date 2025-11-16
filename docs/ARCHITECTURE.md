# Architecture Documentation

## Overview

Ollama Monitor is designed as a modular, asynchronous monitoring system for Ollama AI model servers. It follows a clean architecture pattern with separation of concerns.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Ollama Monitor                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │   CLI Args   │──────▶│  Config      │                   │
│  │  (argparse)  │      │  Validator   │                   │
│  └──────────────┘      │  (Pydantic)  │                   │
│                        └───────┬──────┘                   │
│                                │                            │
│                                ▼                            │
│                      ┌──────────────────┐                  │
│                      │ OllamaMonitor    │                  │
│                      │   (Main Class)   │                  │
│                      └────────┬─────────┘                  │
│                               │                            │
│         ┌────────────────────┼────────────────────┐        │
│         │                    │                    │        │
│         ▼                    ▼                    ▼        │
│  ┌─────────────┐     ┌─────────────┐    ┌──────────────┐ │
│  │  Endpoint   │     │    Load     │    │ Continuous   │ │
│  │   Checks    │     │   Testing   │    │ Monitoring   │ │
│  │  (async)    │     │   (async)   │    │   (async)    │ │
│  └──────┬──────┘     └──────┬──────┘    └──────┬───────┘ │
│         │                   │                   │         │
│         └───────────────────┴───────────────────┘         │
│                            │                              │
│         ┌──────────────────┼──────────────────┐          │
│         │                  │                  │          │
│         ▼                  ▼                  ▼          │
│  ┌────────────┐   ┌──────────────┐   ┌─────────────┐    │
│  │ Prometheus │   │   Alerting   │   │   Reports   │    │
│  │  Metrics   │   │   (Webhook)  │   │ (Multiple)  │    │
│  └────────────┘   └──────────────┘   └─────────────┘    │
│                                                           │
└───────────────────────────────────────────────────────────┘

           │                │                │
           ▼                ▼                ▼
    ┌──────────┐    ┌─────────────┐   ┌────────────┐
    │Prometheus│    │   Webhook   │   │   Files    │
    │  Server  │    │  Endpoints  │   │ (TXT/JSON/ │
    │          │    │(Slack, etc) │   │  CSV/HTML) │
    └──────────┘    └─────────────┘   └────────────┘
```

## Core Components

### 1. Configuration Management

**Files**: `config_validator.py`, `ollama_monitor.py`

**Responsibilities**:
- Load and parse YAML configuration
- Validate configuration using Pydantic models
- Provide defaults and environment variable overrides
- Type-safe configuration access

**Flow**:
```
YAML File → load_config() → Pydantic Validation → MonitorConfigModel
                                                         ↓
Environment Variables ──────────────────────────────────┤
                                                         ↓
CLI Arguments ──────────────────────────────────────────┘
```

### 2. Monitoring Engine

**File**: `ollama_monitor.py`

**Class**: `OllamaMonitor`

**Key Methods**:
- `check_endpoint()` - Single endpoint health check
- `run_checks()` - Concurrent multi-endpoint checks
- `load_test()` - Performance/load testing
- `continuous_monitoring()` - Long-running monitoring

**Async Architecture**:
```python
async with httpx.AsyncClient() as client:
    tasks = [
        check_endpoint(client, ep1, config1),
        check_endpoint(client, ep2, config2),
        # ...
    ]
    results = await asyncio.gather(*tasks)
```

### 3. Logging System

**File**: `logger_config.py`

**Features**:
- Structured logging support
- JSON format for machine-readable logs
- Text format for human-readable logs
- Context-aware logging with LoggerAdapter

**Configuration**:
```python
setup_logging(log_level="INFO", json_format=True)
```

### 4. Report Generation

**File**: `report_generator.py`

**Formats**:
- **Text**: Human-readable summary
- **JSON**: Machine-parseable data
- **CSV**: Spreadsheet-compatible
- **HTML**: Rich visual reports with charts

**Architecture**:
```python
async def generate_report(results, endpoints, filename, format="text"):
    if format == "json":
        await generate_json_report(...)
    elif format == "csv":
        await generate_csv_report(...)
    elif format == "html":
        await generate_html_report(...)
    else:
        await generate_text_report(...)
```

### 5. Alerting System

**File**: `alerting.py`

**Class**: `AlertManager`

**Features**:
- Webhook-based alerting
- Configurable thresholds
- Failure tracking and statistics
- Consecutive failure detection
- Success rate monitoring

**Alert Triggers**:
1. Consecutive failures ≥ `min_failures`
2. Success rate < `alert_threshold`

### 6. Metrics Export

**Integration**: Prometheus Client

**Metrics**:
- `ollama_endpoint_up` - Endpoint availability (0/1)
- `ollama_request_duration_seconds` - Response time histogram
- `ollama_request_errors_total` - Error counter
- `ollama_request_processing_seconds` - Request processing summary

## Data Flow

### Basic Health Check

```
User Command
    ↓
Parse Arguments
    ↓
Load Configuration → Validate with Pydantic
    ↓
Create OllamaMonitor Instance
    ↓
run_checks() → Multiple async check_endpoint()
    ↓
Collect Results
    ↓
Generate Report (Text/JSON/CSV/HTML)
    ↓
Write to File
```

### Continuous Monitoring

```
User Command (--continuous)
    ↓
Setup Configuration
    ↓
Create OllamaMonitor
    ↓
Setup Signal Handlers (SIGTERM, SIGINT)
    ↓
Start Prometheus HTTP Server (if --prometheus)
    ↓
continuous_monitoring() Loop:
    ├─> run_checks()
    ├─> Update Prometheus Metrics
    ├─> Check Alert Conditions
    ├─> Send Alerts if Needed
    ├─> Wait for Interval or Shutdown Signal
    └─> Repeat
    ↓
Graceful Shutdown on Signal
```

### Load Testing

```
User Command (--load-test)
    ↓
Setup Configuration
    ↓
Create OllamaMonitor
    ↓
load_test(num_requests, concurrency):
    ├─> Create Semaphore (concurrency limit)
    ├─> Launch N concurrent tasks
    ├─> Each task: check_endpoint()
    ├─> Collect response times and status codes
    └─> Calculate statistics (avg, median, p95, min, max)
    ↓
Display Results
```

## Deployment Architectures

### 1. Standalone (Docker)

```
┌─────────────────────┐
│  Ollama Monitor     │
│   (Container)       │
│   Port 8000         │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │Ollama Server │
    │ Port 11434   │
    └──────────────┘
```

### 2. Docker Compose Stack

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Grafana    │────▶│ Prometheus   │────▶│Ollama Monitor│
│  Port 3000   │     │  Port 9090   │     │  Port 8000   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                                           ┌──────────────┐
                                           │Ollama Server │
                                           │ Port 11434   │
                                           └──────────────┘
```

### 3. Kubernetes Cluster

```
┌─────────────────────────────────────────────────┐
│              Kubernetes Cluster                  │
│                                                  │
│  ┌─────────────┐      ┌──────────────┐         │
│  │   Ingress   │      │  Prometheus  │         │
│  │             │      │   Operator   │         │
│  └──────┬──────┘      └──────┬───────┘         │
│         │                    │                  │
│         ▼                    ▼                  │
│  ┌──────────────────────────────────┐          │
│  │    Ollama Monitor Service        │          │
│  │       (ClusterIP)                │          │
│  └────────────┬─────────────────────┘          │
│               │                                 │
│               ▼                                 │
│  ┌──────────────────────────────────┐          │
│  │   Ollama Monitor Deployment      │          │
│  │      (1+ replicas)               │          │
│  └────────────┬─────────────────────┘          │
│               │                                 │
│               ▼                                 │
│  ┌──────────────────────────────────┐          │
│  │      Ollama Service              │          │
│  └──────────────────────────────────┘          │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Security Model

### Defense in Depth

1. **Container Security**:
   - Non-root user (UID 1000)
   - Read-only root filesystem
   - Dropped capabilities
   - No privilege escalation

2. **Network Security**:
   - TLS verification enabled
   - Minimal exposed ports
   - Network policies (Kubernetes)

3. **Configuration Security**:
   - Validation with Pydantic
   - No hardcoded secrets
   - Environment variable support
   - .gitignore for sensitive files

4. **Runtime Security**:
   - Graceful shutdown
   - Error handling
   - Resource limits
   - Health checks

## Performance Characteristics

### Concurrency Model

- **Async I/O**: Non-blocking HTTP requests
- **Semaphore Control**: Bounded concurrency
- **Connection Pooling**: Reusable HTTP connections

### Resource Usage

- **Memory**: ~50-100 MB baseline
- **CPU**: Minimal (<5%) during normal operation
- **Network**: Dependent on check frequency

### Scalability

- **Horizontal**: Multiple monitor instances
- **Vertical**: Increase concurrency limits
- **Endpoints**: Tested with 100+ endpoints

## Error Handling Strategy

### Levels

1. **Retry Logic**: Automatic retry with exponential backoff
2. **Exception Handling**: Graceful degradation
3. **Logging**: Comprehensive error logging
4. **Alerting**: Notify on persistent failures
5. **Metrics**: Track error rates

### Graceful Shutdown

```python
# Signal handlers
SIGTERM → shutdown_event.set()
SIGINT  → shutdown_event.set()

# Monitoring loop
while not shutdown_event.is_set():
    await run_checks()
    await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
```

## Extension Points

### Adding New Report Formats

```python
# report_generator.py
async def generate_xml_report(results, endpoints, filename):
    # Implementation
    pass

# Register in generate_report()
if format == "xml":
    await generate_xml_report(...)
```

### Adding New Alert Channels

```python
# alerting.py
class SlackAlertManager(AlertManager):
    async def send_alert(self, message, severity):
        # Slack-specific implementation
        pass
```

### Custom Metrics

```python
from prometheus_client import Counter

CUSTOM_METRIC = Counter(
    'custom_metric_total',
    'Description of custom metric'
)

# Use in code
CUSTOM_METRIC.inc()
```

## Testing Strategy

### Unit Tests
- Individual function testing
- Mock external dependencies
- Fast execution (<1s)

### Integration Tests
- Component interaction testing
- Mock external services
- Medium execution (1-10s)

### End-to-End Tests
- Full system testing
- Real Ollama instance
- Slow execution (>10s)

## Future Enhancements

1. **Distributed Tracing**: OpenTelemetry integration
2. **Advanced Analytics**: Historical trend analysis
3. **Auto-scaling**: Dynamic endpoint management
4. **Multi-region**: Geographic distribution
5. **Plugin System**: Extensible architecture
