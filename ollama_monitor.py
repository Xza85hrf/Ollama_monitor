import asyncio
import httpx
import json
import time
import logging
import os
import yaml
import argparse
import signal
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from functools import wraps
import statistics
import aiofiles
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configure logging to log info level messages and above, with a specific format
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Read configuration from environment variables or use default values
BASE_URL = os.getenv("OLLAMA_API_BASE", "http://127.0.0.1:11435")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", 10))  # seconds

# Retry configuration
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 2))  # seconds

@dataclass
class EndpointConfig:
    path: str
    method: str = "GET"
    expected_status: int = 200
    expected_content: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None

# Function to set up Prometheus metrics
def setup_prometheus():
    try:
        from prometheus_client import (
            start_http_server,
            Summary,
            Gauge,
            Histogram,
            Counter,
        )

        # Define global metrics variables
        global REQUEST_TIME, ENDPOINT_UP, REQUEST_DURATION, ERROR_COUNTER
        REQUEST_TIME = Summary(
            "ollama_request_processing_seconds", "Time spent processing request"
        )
        ENDPOINT_UP = Gauge("ollama_endpoint_up", "Endpoint availability", ["endpoint"])
        REQUEST_DURATION = Histogram(
            "ollama_request_duration_seconds",
            "Request duration in seconds",
            ["endpoint"],
        )
        ERROR_COUNTER = Counter(
            "ollama_request_errors_total",
            "Total number of request errors",
            ["endpoint"],
        )
        return start_http_server, True
    except ImportError:
        logging.warning(
            "prometheus_client not installed. Prometheus metrics will not be available."
        )
        return None, False

# Asynchronous retry decorator
def async_retry(attempts=RETRY_ATTEMPTS, delay=RETRY_DELAY):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts - 1:
                        raise
                    logging.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)

        return wrapper

    return decorator

# Main class for monitoring endpoints
class OllamaMonitor:
    def __init__(
        self,
        base_url: str,
        endpoints: Dict[str, EndpointConfig],
        timeout: int,
        use_prometheus: bool,
    ):
        self.base_url = base_url
        self.endpoints = endpoints
        self.timeout = timeout
        self.use_prometheus = use_prometheus
        self.shutdown_event = asyncio.Event()

    @async_retry()
    async def check_endpoint(
        self, client: httpx.AsyncClient, endpoint: str, config: EndpointConfig
    ) -> Tuple[float, int]:
        full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        logging.info(f"\nTesting URL: {full_url}")

        try:
            start_time = time.time()
            response = await client.request(
                config.method,
                full_url,
                headers=config.headers,
                json=config.body,
                timeout=self.timeout,
            )
            response_time = time.time() - start_time

            if self.use_prometheus:
                REQUEST_DURATION.labels(endpoint=endpoint).observe(response_time)

            logging.info(f"Status code: {response.status_code}")
            logging.info(f"Response time: {response_time:.2f} seconds")
            logging.info(f"Headers: {response.headers}")

            if response.headers.get("Content-Type") == "application/json":
                try:
                    data = response.json()
                    logging.info("JSON Response:")
                    logging.info(json.dumps(data, indent=4))
                except json.JSONDecodeError:
                    logging.warning("Failed to parse JSON response")
            else:
                logging.info(
                    f"Response: {response.text[:500]}"
                )  # Print first 500 characters for brevity

            if response.status_code == config.expected_status:
                if (
                    config.expected_content
                    and config.expected_content not in response.text
                ):
                    logging.warning(
                        f"Expected content not found: {config.expected_content}"
                    )
                    if self.use_prometheus:
                        ENDPOINT_UP.labels(endpoint=endpoint).set(0)
                else:
                    logging.info("Endpoint is functioning correctly.")
                    if self.use_prometheus:
                        ENDPOINT_UP.labels(endpoint=endpoint).set(1)
            else:
                logging.warning(f"Unexpected status code: {response.status_code}")
                if self.use_prometheus:
                    ENDPOINT_UP.labels(endpoint=endpoint).set(0)
                    ERROR_COUNTER.labels(endpoint=endpoint).inc()

            return response_time, response.status_code

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            if self.use_prometheus:
                ENDPOINT_UP.labels(endpoint=endpoint).set(0)
                ERROR_COUNTER.labels(endpoint=endpoint).inc()
            raise

    # Run checks for all endpoints
    async def run_checks(self) -> List[Any]:
        async with httpx.AsyncClient(verify=True) as client:
            tasks = [
                self.check_endpoint(client, endpoint, config)
                for endpoint, config in self.endpoints.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

    # Perform load testing
    async def load_test(self, num_requests: int, concurrency: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(verify=True) as client:
            semaphore = asyncio.Semaphore(concurrency)
            response_times = []
            status_codes = []

            async def bounded_check():
                async with semaphore:
                    try:
                        response_time, status_code = await self.check_endpoint(
                            client, "/", self.endpoints["/"]
                        )
                        response_times.append(response_time)
                        status_codes.append(status_code)
                    except Exception as e:
                        logging.error(f"Request failed: {str(e)}")
                        status_codes.append(None)

            tasks = [bounded_check() for _ in range(num_requests)]
            await asyncio.gather(*tasks)

            successful_requests = sum(1 for code in status_codes if code == 200)
            failed_requests = num_requests - successful_requests

            if response_times:
                avg_time = statistics.mean(response_times)
                median_time = statistics.median(response_times)
                p95_time = statistics.quantiles(response_times, n=20)[
                    -1
                ]  # 95th percentile
                min_time = min(response_times)
                max_time = max(response_times)
            else:
                avg_time = median_time = p95_time = min_time = max_time = 0

            return {
                "total_requests": num_requests,
                "concurrency": concurrency,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "average_response_time": avg_time,
                "median_response_time": median_time,
                "p95_response_time": p95_time,
                "min_response_time": min_time,
                "max_response_time": max_time,
            }

    # Continuous monitoring with specified interval
    async def continuous_monitoring(self, interval: int) -> None:
        """Run continuous monitoring with graceful shutdown support."""
        logging.info(f"Starting continuous monitoring (interval: {interval} seconds)")
        while not self.shutdown_event.is_set():
            logging.info("Running checks...")
            try:
                await self.run_checks()
            except Exception as e:
                logging.error(f"Error during monitoring: {e}")

            # Wait for interval or shutdown event
            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=interval
                )
            except asyncio.TimeoutError:
                continue

        logging.info("Continuous monitoring stopped gracefully")

# Generate a report from results and save to a file
async def generate_report(results: List[tuple], filename: str):
    report = "Ollama Monitor Report\n"
    report += "=====================\n\n"

    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            report += f"Endpoint {idx + 1}: An error occurred - {str(result)}\n"
        elif isinstance(result, tuple):
            # Extraer los valores de la tupla
            response_time, status_code = result
            report += f"Endpoint {idx + 1}:\n"
            report += f"  Status Code: {status_code}\n"
            report += f"  Response Time: {response_time:.2f} seconds\n\n"
        else:
            report += f"Endpoint {idx + 1}: Unexpected result format\n"

    async with aiofiles.open(filename, mode="w") as f:
        await f.write(report)

    logging.info(f"Report generated: {filename}")

# Load configuration from a YAML file
def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, "r") as file:
        return yaml.safe_load(file)

# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Test connectivity to the Ollama server."
    )
    parser.add_argument(
        "--url", type=str, default=BASE_URL, help="Base URL of the Ollama server"
    )
    parser.add_argument("--config", type=str, help="Path to YAML configuration file")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Timeout for each request in seconds",
    )
    parser.add_argument(
        "--prometheus", action="store_true", help="Enable Prometheus metrics export"
    )
    parser.add_argument("--load-test", action="store_true", help="Perform load testing")
    parser.add_argument(
        "--num-requests",
        type=int,
        default=100,
        help="Number of requests for load testing",
    )
    parser.add_argument(
        "--concurrency", type=int, default=10, help="Concurrency level for load testing"
    )
    parser.add_argument(
        "--continuous", action="store_true", help="Run continuous monitoring"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval for continuous monitoring in seconds",
    )
    return parser.parse_args()

# Main function to orchestrate the monitoring and testing
async def main() -> None:
    args = parse_arguments()

    prometheus_available = False
    if args.prometheus:
        start_http_server, prometheus_available = setup_prometheus()
        if prometheus_available:
            start_http_server(8000)

    if args.config:
        config = load_config(args.config)
        base_url = config.get("base_url", args.url)
        endpoints = {
            k: EndpointConfig(**v) for k, v in config.get("endpoints", {}).items()
        }
        timeout = config.get("timeout", args.timeout)
    else:
        base_url = args.url
        endpoints = {"/": EndpointConfig("/")}
        timeout = args.timeout

    monitor = OllamaMonitor(base_url, endpoints, timeout, prometheus_available)

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        logging.info(f"Received signal {sig}, initiating graceful shutdown...")
        monitor.shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        if args.load_test:
            logging.info(
                f"Starting load test with {args.num_requests} requests and concurrency {args.concurrency}"
            )
            results = await monitor.load_test(args.num_requests, args.concurrency)
            logging.info("Load Test Results:")
            for key, value in results.items():
                if isinstance(value, float):
                    logging.info(f"{key}: {value:.3f}")
                else:
                    logging.info(f"{key}: {value}")
        elif args.continuous:
            logging.info(
                f"Starting continuous monitoring with interval of {args.interval} seconds"
            )
            await monitor.continuous_monitoring(args.interval)
        else:
            results = await monitor.run_checks()
            await generate_report(results, "ollama_monitor_report.txt")
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down...")
    finally:
        logging.info("Shutdown complete")

# Run the main function in an asyncio event loop
if __name__ == "__main__":
    asyncio.run(main())
