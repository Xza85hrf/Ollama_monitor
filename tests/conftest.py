"""Pytest configuration and fixtures."""
import pytest
from ollama_monitor import EndpointConfig, OllamaMonitor


@pytest.fixture
def base_url():
    """Return base URL for testing."""
    return "http://localhost:11434"


@pytest.fixture
def endpoint_config():
    """Return basic endpoint configuration."""
    return EndpointConfig(
        path="/",
        method="GET",
        expected_status=200,
        expected_content="Ollama is running"
    )


@pytest.fixture
def endpoints(endpoint_config):
    """Return endpoints dictionary."""
    return {"/": endpoint_config}


@pytest.fixture
def monitor(base_url, endpoints):
    """Return OllamaMonitor instance."""
    return OllamaMonitor(
        base_url=base_url,
        endpoints=endpoints,
        timeout=10,
        use_prometheus=False
    )


@pytest.fixture
def api_generate_config():
    """Return API generate endpoint configuration."""
    return EndpointConfig(
        path="/api/generate",
        method="POST",
        expected_status=200,
        headers={"Content-Type": "application/json"},
        body={
            "model": "llama2",
            "prompt": "Test prompt",
            "stream": False
        }
    )
