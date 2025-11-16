"""Ollama Monitor - Comprehensive monitoring tool for Ollama AI model servers."""
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
from dotenv import load_dotenv

# Import new modules
from logger_config import setup_logging
from config_validator import validate_config, MonitorConfigModel, EndpointConfigModel
from report_generator import generate_report as generate_report_multi_format
from alerting import AlertManager

# Load environment variables from a .env file
load_dotenv()

# Read configuration from environment variables or use default values
BASE_URL = os.getenv("OLLAMA_API_BASE", "http://127.0.0.1:11435")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", 10))  # seconds

# Retry configuration
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 2))  # seconds

# Get logger
logger = logging.getLogger(__name__)


@dataclass
class EndpointConfig:
    """Endpoint configuration (for backward compatibility)."""
    path: str
    method: str = "GET"
    expected_status: int = 200
    expected_content: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None


# Function to set up Prometheus metrics
def setup_prometheus():
    """Set up Prometheus metrics."""
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
        logger.warning(
            "prometheus_client not installed. Prometheus metrics will not be available."
        )
        return None, False


# Asynchronous retry decorator
def async_retry(attempts=RETRY_ATTEMPTS, delay=RETRY_DELAY):
    """Retry decorator for async functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts - 1:
                        raise
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)

        return wrapper

    return decorator


# Main class for monitoring endpoints
class OllamaMonitor:
    """Main monitoring class for Ollama endpoints."""

    def __init__(
        self,
        base_url: str,
        endpoints: Dict[str, EndpointConfig],
        timeout: int,
        use_prometheus: bool,
        alert_manager: Optional[AlertManager] = None,
    ):
        """
        Initialize OllamaMonitor.

        Args:
            base_url: Base URL of Ollama server
            endpoints: Dictionary of endpoints to monitor
            timeout: Request timeout in seconds
            use_prometheus: Whether to export Prometheus metrics
            alert_manager: Optional AlertManager for sending alerts
        """
        self.base_url = base_url
        self.endpoints = endpoints
        self.timeout = timeout
        self.use_prometheus = use_prometheus
        self.alert_manager = alert_manager
        self.shutdown_event = asyncio.Event()

    @async_retry()
    async def check_endpoint(
        self, client: httpx.AsyncClient, endpoint: str, config: EndpointConfig
    ) -> Tuple[float, int]:
        """
        Check a single endpoint.

        Args:
            client: HTTP client
            endpoint: Endpoint path
            config: Endpoint configuration

        Returns:
            Tuple of (response_time, status_code)
        """
        full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        logger.info(f"Testing URL: {full_url}", extra={"endpoint": endpoint})

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

            logger.info(
                f"Status: {response.status_code}, Time: {response_time:.2f}s",
                extra={
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_time": response_time
                }
            )

            if response.headers.get("Content-Type") == "application/json":
                try:
                    data = response.json()
                    logger.debug(f"JSON Response: {json.dumps(data, indent=2)}")
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response")
            else:
                logger.debug(f"Response: {response.text[:500]}")

            # Determine if check was successful
            success = response.status_code == config.expected_status

            if success:
                if (
                    config.expected_content
                    and config.expected_content not in response.text
                ):
                    logger.warning(
                        f"Expected content not found: {config.expected_content}"
                    )
                    success = False
                    if self.use_prometheus:
                        ENDPOINT_UP.labels(endpoint=endpoint).set(0)
                else:
                    logger.info("Endpoint is functioning correctly.")
                    if self.use_prometheus:
                        ENDPOINT_UP.labels(endpoint=endpoint).set(1)
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")
                if self.use_prometheus:
                    ENDPOINT_UP.labels(endpoint=endpoint).set(0)
                    ERROR_COUNTER.labels(endpoint=endpoint).inc()

            # Send alert if configured
            if self.alert_manager:
                error_msg = None if success else f"Status code: {response.status_code}"
                await self.alert_manager.check_and_alert(endpoint, success, error_msg)

            return response_time, response.status_code

        except Exception as e:
            logger.error(f"An error occurred: {str(e)}", extra={"endpoint": endpoint})
            if self.use_prometheus:
                ENDPOINT_UP.labels(endpoint=endpoint).set(0)
                ERROR_COUNTER.labels(endpoint=endpoint).inc()

            # Send alert for exception
            if self.alert_manager:
                await self.alert_manager.check_and_alert(endpoint, False, str(e))

            raise

    async def run_checks(self) -> List[Any]:
        """
        Run checks for all endpoints.

        Returns:
            List of check results
        """
        async with httpx.AsyncClient(verify=True) as client:
            tasks = [
                self.check_endpoint(client, endpoint, config)
                for endpoint, config in self.endpoints.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

    async def load_test(self, num_requests: int, concurrency: int) -> Dict[str, Any]:
        """
        Perform load testing.

        Args:
            num_requests: Total number of requests
            concurrency: Number of concurrent requests

        Returns:
            Dictionary with load test statistics
        """
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
                        logger.error(f"Request failed: {str(e)}")
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

    async def continuous_monitoring(self, interval: int) -> None:
        """
        Run continuous monitoring with graceful shutdown support.

        Args:
            interval: Interval between checks in seconds
        """
        logger.info(f"Starting continuous monitoring (interval: {interval} seconds)")
        while not self.shutdown_event.is_set():
            logger.info("Running checks...")
            try:
                await self.run_checks()

                # Log alert statistics if available
                if self.alert_manager:
                    stats = self.alert_manager.get_stats()
                    if stats:
                        logger.info(f"Alert statistics: {stats}")

            except Exception as e:
                logger.error(f"Error during monitoring: {e}")

            # Wait for interval or shutdown event
            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=interval
                )
            except asyncio.TimeoutError:
                continue

        logger.info("Continuous monitoring stopped gracefully")


def load_config(config_file: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Configuration dictionary
    """
    with open(config_file, "r") as file:
        return yaml.safe_load(file)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Monitor and test connectivity to Ollama server."
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
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "csv", "html"],
        default="text",
        help="Report output format (default: text)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: auto-generated based on format)",
    )
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Enable JSON structured logging",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration file and exit",
    )
    return parser.parse_args()


async def main() -> None:
    """Main function to orchestrate the monitoring and testing."""
    args = parse_arguments()

    # Setup logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    json_format = args.json_logs or os.getenv("LOG_FORMAT", "").lower() == "json"
    setup_logging(log_level=log_level, json_format=json_format)

    logger.info("Ollama Monitor starting...")

    # Load and validate configuration
    validated_config: Optional[MonitorConfigModel] = None
    alert_manager: Optional[AlertManager] = None

    if args.config:
        try:
            config_dict = load_config(args.config)

            # Validate configuration with Pydantic
            try:
                validated_config = validate_config(config_dict)
                logger.info("Configuration validated successfully")

                # Just validate and exit if requested
                if args.validate_config:
                    logger.info("Configuration is valid!")
                    print("✓ Configuration is valid!")
                    return

            except Exception as e:
                logger.error(f"Configuration validation failed: {e}")
                if args.validate_config:
                    print(f"✗ Configuration validation failed: {e}")
                    return
                raise

            # Use validated config
            base_url = str(validated_config.base_url)
            timeout = validated_config.timeout

            # Convert Pydantic models to EndpointConfig
            endpoints = {}
            for path, ep_config in validated_config.endpoints.items():
                endpoints[path] = EndpointConfig(
                    path=ep_config.path,
                    method=ep_config.method,
                    expected_status=ep_config.expected_status,
                    expected_content=ep_config.expected_content,
                    headers=ep_config.headers,
                    body=ep_config.body,
                )

            # Setup alerting if configured
            if validated_config.alerting and validated_config.alerting.enabled:
                alert_config = validated_config.alerting
                alert_manager = AlertManager(
                    webhook_url=str(alert_config.webhook_url) if alert_config.webhook_url else None,
                    alert_on_failure=alert_config.alert_on_failure,
                    alert_threshold=alert_config.alert_threshold,
                    min_failures=alert_config.min_failures,
                )
                logger.info("Alerting enabled via webhook")

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {args.config}")
            return
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration file: {e}")
            return
    else:
        # Use defaults from command line
        base_url = args.url
        endpoints = {"/": EndpointConfig("/")}
        timeout = args.timeout

    # Setup Prometheus if requested
    prometheus_available = False
    if args.prometheus:
        start_http_server, prometheus_available = setup_prometheus()
        if prometheus_available:
            start_http_server(8000)
            logger.info("Prometheus metrics available on port 8000")

    # Create monitor instance
    monitor = OllamaMonitor(
        base_url=base_url,
        endpoints=endpoints,
        timeout=timeout,
        use_prometheus=prometheus_available,
        alert_manager=alert_manager,
    )

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        monitor.shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        if args.load_test:
            logger.info(
                f"Starting load test: {args.num_requests} requests, concurrency {args.concurrency}"
            )
            results = await monitor.load_test(args.num_requests, args.concurrency)
            logger.info("Load Test Results:")
            for key, value in results.items():
                if isinstance(value, float):
                    logger.info(f"{key}: {value:.3f}")
                else:
                    logger.info(f"{key}: {value}")

        elif args.continuous:
            logger.info(
                f"Starting continuous monitoring with interval of {args.interval} seconds"
            )
            await monitor.continuous_monitoring(args.interval)

        else:
            # Run single check and generate report
            logger.info("Running endpoint checks...")
            results = await monitor.run_checks()

            # Generate output filename based on format
            if args.output:
                output_file = args.output
            else:
                extensions = {
                    "text": "txt",
                    "json": "json",
                    "csv": "csv",
                    "html": "html"
                }
                output_file = f"ollama_monitor_report.{extensions[args.format]}"

            # Generate report in requested format
            await generate_report_multi_format(
                results=results,
                endpoints=endpoints,
                filename=output_file,
                format=args.format
            )
            logger.info(f"Report generated: {output_file} (format: {args.format})")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
