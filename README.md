# Ollama Monitor

Ollama Monitor is a Python tool designed to help developers monitor the connectivity and performance of an Ollama server. Whether you're testing in development or conducting load tests in production, this tool ensures your API endpoints are healthy and functioning as expected.

## Features

- **Endpoint Health Checks**: Monitor API endpoints and measure their response times.
- **Load Testing**: Test the load capacity of your Ollama server with customizable concurrency levels.
- **Prometheus Metrics Export**: Easily expose performance metrics in Prometheus format.
- **Configurable via YAML or CLI**: Customize your tests and settings with a configuration file or command-line arguments.

## Installation

### Prerequisites

- Python 3.12 or higher
- Docker (optional, for containerized deployment)

### Install Locally

1. Clone this repository:
   ```bash
   git clone https://github.com/your-repo/ollama-monitor.git
   cd ollama-monitor
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Docker Setup

1. Build the Docker image:
   ```bash
   docker build -t ollama-monitor .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 ollama-monitor
   ```

This will expose Prometheus metrics on port 8000.

## Configuration

You can configure the Ollama Monitor via a YAML file or use command-line options. Below is a minimal example configuration file:

### `config.yaml` Example:

```yaml
base_url: "http://host.docker.internal:11434"
timeout: 30
endpoints:
  "/":
    path: "/"
    method: "GET"
    expected_status: 200
  "/api/generate":
    path: "/api/generate"
    method: "POST"
    expected_status: 200
    headers:
      Content-Type: "application/json"
    body: {"model": "llama3.1", "prompt": "Provide a summary of AI", "format": "json", "stream": false}
```

## Usage

### Basic Check

Run the monitor using a default configuration:
```bash
python ollama_monitor.py
```

### Using a Custom Configuration File

You can specify a custom configuration file:
```bash
python ollama_monitor.py --config config.yaml
```

### Running with Prometheus Metrics

Enable Prometheus metrics export:
```bash
python ollama_monitor.py --config config.yaml --prometheus
```

## Logging

Logs are streamed to the console (`/dev/stdout`). A typical log entry includes:

- Endpoint URL
- Response status code
- Response time
- Errors (if any)

## Load Testing

To perform load testing, specify the number of requests and concurrency level:
```bash
python ollama_monitor.py --load-test --num-requests 1000 --concurrency 20
```

## Environment Variables

| Variable          | Description                                          | Default                  |
|-------------------|------------------------------------------------------|--------------------------|
| `OLLAMA_API_BASE`  | Base URL of the Ollama server                        | `http://127.0.0.1:11435`  |
| `DEFAULT_TIMEOUT`  | Request timeout in seconds                           | `10`                     |
| `RETRY_ATTEMPTS`   | Number of retry attempts                             | `3`                      |
| `RETRY_DELAY`      | Delay between retries in seconds                     | `2`                      |

## Report Generation

The monitor generates reports summarizing endpoint performance, including response times and status codes. Example report output:
```
Ollama Monitor Report
=====================

Endpoint 1:
  Status Code: 200
  Response Time: 0.75 seconds

Endpoint 2: An error occurred - TimeoutException
```

## Contributing

Contributions are welcome! Feel free to submit pull requests or issues.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
