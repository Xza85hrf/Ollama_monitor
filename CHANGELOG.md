# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pydantic-based configuration validation
- Structured logging with JSON format support
- Multiple report formats (JSON, CSV, HTML)
- Webhook alerting integration with configurable thresholds
- Kubernetes deployment manifests
- Comprehensive unit test suite
- GitHub Actions CI/CD pipeline
- Pre-commit hooks for code quality
- Docker Compose stack with Prometheus and Grafana
- Security scanning with Trivy
- Type hints throughout codebase
- Graceful shutdown handling with signal handlers
- `.dockerignore` for optimized builds
- Development dependencies in `requirements-dev.txt`

### Changed
- Dockerfile now runs as non-root user (UID 1000)
- Logging configuration uses `StreamHandler` instead of file-based
- Continuous monitoring with proper shutdown support
- SSL/TLS verification enabled in httpx clients
- Improved error handling in monitoring loops

### Security
- Docker health checks added
- Non-root container execution
- SSL certificate verification enforced
- Read-only root filesystem in Kubernetes
- Security context with dropped capabilities

## [1.0.0] - 2024-10-XX

### Added
- Initial release
- Basic endpoint health monitoring
- Load testing capabilities
- Prometheus metrics export
- YAML configuration support
- Async/await architecture with httpx
- Retry logic with exponential backoff
- Multiple endpoint monitoring
- Response time tracking (mean, median, p95)
- Docker support
- Environment variable configuration

### Features
- GET/POST request support
- Custom headers and request bodies
- Expected status code validation
- Content verification
- Concurrent endpoint testing
- Continuous monitoring mode
- Report generation

## [0.1.0] - 2024-XX-XX

### Added
- Project initialization
- Basic monitoring script
- README documentation
- MIT License

---

## Version History

- **Unreleased** - Enhanced security, testing, DevOps, and features
- **1.0.0** - Initial stable release with core functionality
- **0.1.0** - Initial development version

## Migration Guide

### Upgrading to Unreleased

#### Configuration Changes

If you were using the old configuration format, update to include validation:

**Old** (still supported):
```yaml
base_url: "http://localhost:11434"
timeout: 30
endpoints:
  "/":
    path: "/"
    method: "GET"
```

**New** (with alerting):
```yaml
base_url: "http://localhost:11434"
timeout: 30
endpoints:
  "/":
    path: "/"
    method: "GET"
    expected_status: 200
alerting:
  enabled: true
  webhook_url: "https://hooks.example.com/webhook"
  alert_threshold: 0.95
```

#### Docker Changes

The Docker image now runs as non-root. If you're mounting volumes, ensure permissions are correct:

```bash
# Fix permissions for mounted config
chmod 644 config.yaml
```

#### Environment Variables

New environment variables available:

```bash
LOG_LEVEL=INFO          # Set logging level
LOG_FORMAT=json         # Enable JSON logging
```

## Breaking Changes

None in current unreleased version. All changes are backward compatible.

## Deprecation Notices

None at this time.

## Contributors

Thank you to all contributors who helped make this project better:

- Initial development and Docker support: [@mnofresno](https://github.com/mnofresno)
- Project maintainer: [@Xza85hrf](https://github.com/Xza85hrf)

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute.

---

[Unreleased]: https://github.com/Xza85hrf/Ollama_monitor/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Xza85hrf/Ollama_monitor/releases/tag/v1.0.0
[0.1.0]: https://github.com/Xza85hrf/Ollama_monitor/releases/tag/v0.1.0
