"""Unit tests for ollama_monitor module."""
import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch
from ollama_monitor import (
    OllamaMonitor,
    EndpointConfig,
    async_retry,
    load_config,
)


class TestEndpointConfig:
    """Test EndpointConfig dataclass."""

    def test_default_values(self):
        """Test EndpointConfig with default values."""
        config = EndpointConfig(path="/test")
        assert config.path == "/test"
        assert config.method == "GET"
        assert config.expected_status == 200
        assert config.expected_content is None
        assert config.headers is None
        assert config.body is None

    def test_custom_values(self):
        """Test EndpointConfig with custom values."""
        config = EndpointConfig(
            path="/api/generate",
            method="POST",
            expected_status=201,
            expected_content="success",
            headers={"Content-Type": "application/json"},
            body={"key": "value"}
        )
        assert config.path == "/api/generate"
        assert config.method == "POST"
        assert config.expected_status == 201
        assert config.expected_content == "success"
        assert config.headers == {"Content-Type": "application/json"}
        assert config.body == {"key": "value"}


class TestAsyncRetry:
    """Test async_retry decorator."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test successful execution on first attempt."""
        call_count = 0

        @async_retry(attempts=3, delay=0.01)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry logic on failure."""
        call_count = 0

        @async_retry(attempts=3, delay=0.01)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"

        result = await failing_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test that exception is raised after exhausting retries."""
        @async_retry(attempts=3, delay=0.01)
        async def always_failing_func():
            raise Exception("Permanent error")

        with pytest.raises(Exception, match="Permanent error"):
            await always_failing_func()


class TestOllamaMonitor:
    """Test OllamaMonitor class."""

    @pytest.mark.asyncio
    async def test_check_endpoint_success(self, monitor, endpoint_config):
        """Test successful endpoint check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Ollama is running"
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.json.side_effect = Exception("Not JSON")

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        response_time, status_code = await monitor.check_endpoint(
            mock_client, "/", endpoint_config
        )

        assert status_code == 200
        assert response_time >= 0
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_endpoint_wrong_status(self, monitor, endpoint_config):
        """Test endpoint check with unexpected status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.json.side_effect = Exception("Not JSON")

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        response_time, status_code = await monitor.check_endpoint(
            mock_client, "/", endpoint_config
        )

        assert status_code == 500
        assert response_time >= 0

    @pytest.mark.asyncio
    async def test_check_endpoint_missing_content(self, monitor):
        """Test endpoint check with missing expected content."""
        config = EndpointConfig(
            path="/",
            method="GET",
            expected_status=200,
            expected_content="Expected text"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Different text"
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.json.side_effect = Exception("Not JSON")

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        response_time, status_code = await monitor.check_endpoint(
            mock_client, "/", config
        )

        assert status_code == 200
        assert response_time >= 0

    @pytest.mark.asyncio
    async def test_check_endpoint_json_response(self, monitor, api_generate_config):
        """Test endpoint check with JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"response": "test"}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json = Mock(return_value={"response": "test"})

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        response_time, status_code = await monitor.check_endpoint(
            mock_client, "/api/generate", api_generate_config
        )

        assert status_code == 200
        assert response_time >= 0

    @pytest.mark.asyncio
    async def test_run_checks(self, monitor):
        """Test running checks for all endpoints."""
        with patch.object(monitor, 'check_endpoint') as mock_check:
            mock_check.return_value = (0.5, 200)

            results = await monitor.run_checks()

            assert len(results) == 1
            assert results[0] == (0.5, 200)

    @pytest.mark.asyncio
    async def test_load_test(self, monitor):
        """Test load testing functionality."""
        with patch.object(monitor, 'check_endpoint') as mock_check:
            mock_check.return_value = (0.5, 200)

            results = await monitor.load_test(num_requests=10, concurrency=2)

            assert results["total_requests"] == 10
            assert results["concurrency"] == 2
            assert results["successful_requests"] == 10
            assert results["failed_requests"] == 0
            assert results["average_response_time"] > 0
            assert results["median_response_time"] > 0
            assert results["min_response_time"] > 0
            assert results["max_response_time"] > 0

    @pytest.mark.asyncio
    async def test_load_test_with_failures(self, monitor):
        """Test load testing with some failures."""
        call_count = 0

        async def mock_check_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Simulated failure")
            return (0.5, 200)

        with patch.object(monitor, 'check_endpoint', side_effect=mock_check_with_failures):
            results = await monitor.load_test(num_requests=10, concurrency=2)

            assert results["total_requests"] == 10
            assert results["successful_requests"] == 5
            assert results["failed_requests"] == 5


class TestConfigLoading:
    """Test configuration loading."""

    def test_load_config_valid_yaml(self, tmp_path):
        """Test loading valid YAML configuration."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
base_url: "http://localhost:11434"
timeout: 30
endpoints:
  "/":
    path: "/"
    method: "GET"
    expected_status: 200
""")

        config = load_config(str(config_file))

        assert config["base_url"] == "http://localhost:11434"
        assert config["timeout"] == 30
        assert "/" in config["endpoints"]

    def test_load_config_file_not_found(self):
        """Test loading non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")


class TestPrometheusIntegration:
    """Test Prometheus metrics integration."""

    def test_monitor_with_prometheus(self, base_url, endpoints):
        """Test creating monitor with Prometheus enabled."""
        monitor = OllamaMonitor(
            base_url=base_url,
            endpoints=endpoints,
            timeout=10,
            use_prometheus=True
        )
        assert monitor.use_prometheus is True

    def test_monitor_without_prometheus(self, monitor):
        """Test creating monitor without Prometheus."""
        assert monitor.use_prometheus is False
