# Ollama Monitor

Ollama Monitor is a Python script designed to test connectivity and performance of an Ollama server. It provides functionality for endpoint checking, load testing, and optional Prometheus metrics export.

## Features

- Endpoint health checks
- Load testing
- Prometheus metrics export (optional)
- Configurable via YAML file or command-line arguments

## Requirements

- Python 3.7+
- Required Python packages:
  - httpx
  - pyyaml
  - prometheus_client (optional, for Prometheus metrics)

## Installation

1. Clone this repository or download the `ollama_monitor.py` script.
2. Install the required packages:

```bash
pip install httpx pyyaml prometheus_client
```

## Usage

### Basic Usage

To run a basic check on the default Ollama endpoint:

```bash
python ollama_monitor.py
```

### Using a Configuration File

Create a YAML configuration file (e.g., `config.yaml`) with the following structure:

```yaml
base_url: "http://127.0.0.1:11435"
timeout: 10
endpoints:
  "/":
    path: "/"
    method: "GET"
    expected_status: 200
  "/api/generate":
    path: "/api/generate"
    method: "POST"
    expected_status: 200
```

Then run the script with the configuration file:

```bash
python ollama_monitor.py --config config.yaml
```

### Command-line Arguments

- `--url`: Base URL of the Ollama server (default: http://127.0.0.1:11435)
- `--config`: Path to YAML configuration file
- `--timeout`: Timeout for each request in seconds (default: 10)
- `--prometheus`: Enable Prometheus metrics export
- `--load-test`: Perform load testing
- `--num-requests`: Number of requests for load testing (default: 100)
- `--concurrency`: Concurrency level for load testing (default: 10)

### Load Testing

To perform a load test:

```bash
python ollama_monitor.py --load-test --num-requests 1000 --concurrency 20
```

### Enabling Prometheus Metrics

To enable Prometheus metrics export:

```bash
python ollama_monitor.py --prometheus
```

This will start a Prometheus metrics server on port 8000.

## Environment Variables

- `OLLAMA_API_BASE`: Base URL of the Ollama server (default: http://127.0.0.1:11435)
- `RETRY_ATTEMPTS`: Number of retry attempts for failed requests (default: 3)
- `RETRY_DELAY`: Delay between retry attempts in milliseconds (default: 2000)

## Output

The script provides detailed logging output, including:

- Endpoint health check results
- Response times
- Status codes
- Headers
- Response content (truncated for brevity)

For load tests, a summary is provided with:

- Total number of requests
- Concurrency level
- Number of successful and failed requests
- Average, minimum, and maximum response times

## Extending the Script

The `OllamaMonitor` class can be extended to add more functionality or customize the behavior of the checks and load tests. The `EndpointConfig` dataclass can be modified to include additional configuration options for each endpoint.

## Troubleshooting

- If you encounter SSL certificate verification errors, you may need to set the `SSL_CERT_FILE` environment variable to the path of your SSL certificate file.
- Ensure that the Ollama server is running and accessible from the machine running the script.
- Check firewall settings if you're unable to connect to the Ollama server.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).
