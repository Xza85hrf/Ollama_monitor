"""Tests for model_monitor module."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, Mock
import httpx

from model_monitor import ModelInfo, ModelMonitor, format_model_report


TAGS_RESPONSE = {
    "models": [
        {
            "name": "llama3:8b",
            "size": 4661224448,
            "digest": "abc123",
            "modified_at": "2024-01-15T10:30:00Z",
        }
    ]
}

PS_RESPONSE = {
    "models": [
        {
            "name": "llama3:8b",
            "size": 4661224448,
            "digest": "abc123",
            "modified_at": "2024-01-15T10:30:00Z",
            "size_vram": 4661224448,
            "expires_at": "2024-01-15T11:30:00Z",
        }
    ]
}


def _mock_client(response_data):
    """Create a mock httpx.AsyncClient returning given JSON."""
    mock_response = Mock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = Mock()

    client = AsyncMock()
    client.get.return_value = mock_response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


class TestModelInfo:
    """Test ModelInfo dataclass."""

    def test_defaults(self):
        info = ModelInfo(name="test", size=1000, modified_at="2024-01-01", digest="abc")
        assert info.loaded is False
        assert info.vram_bytes is None
        assert info.expires_at is None

    def test_all_fields(self):
        info = ModelInfo(
            name="test", size=1000, modified_at="2024-01-01", digest="abc",
            loaded=True, vram_bytes=2000, expires_at="2024-01-02",
        )
        assert info.loaded is True
        assert info.vram_bytes == 2000


class TestModelMonitor:
    """Test ModelMonitor class."""

    @pytest.fixture
    def monitor(self):
        return ModelMonitor(base_url="http://localhost:11434", timeout=10)

    @pytest.mark.asyncio
    async def test_get_available_models(self, monitor):
        with patch("model_monitor.httpx.AsyncClient", return_value=_mock_client(TAGS_RESPONSE)):
            models = await monitor.get_available_models()

        assert len(models) == 1
        assert models[0].name == "llama3:8b"
        assert models[0].size == 4661224448
        assert models[0].loaded is False
        assert models[0].vram_bytes is None

    @pytest.mark.asyncio
    async def test_get_running_models(self, monitor):
        with patch("model_monitor.httpx.AsyncClient", return_value=_mock_client(PS_RESPONSE)):
            models = await monitor.get_running_models()

        assert len(models) == 1
        assert models[0].name == "llama3:8b"
        assert models[0].loaded is True
        assert models[0].vram_bytes == 4661224448
        assert models[0].expires_at == "2024-01-15T11:30:00Z"

    @pytest.mark.asyncio
    async def test_get_model_health(self, monitor):
        with patch("model_monitor.httpx.AsyncClient") as mock_cls:
            # First call (get_available_models) returns tags, second (get_running_models) returns ps
            mock_cls.return_value = _mock_client(TAGS_RESPONSE)
            # We need separate clients for each call, so patch side_effect
            mock_cls.side_effect = [
                _mock_client(TAGS_RESPONSE),
                _mock_client(PS_RESPONSE),
            ]
            health = await monitor.get_model_health()

        assert health["summary"]["total_available"] == 1
        assert health["summary"]["total_loaded"] == 1
        assert health["summary"]["total_vram_bytes"] == 4661224448

    @pytest.mark.asyncio
    async def test_get_available_models_http_error(self, monitor):
        client = AsyncMock()
        client.get.side_effect = httpx.RequestError("Connection refused")
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        with patch("model_monitor.httpx.AsyncClient", return_value=client):
            models = await monitor.get_available_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_get_running_models_http_error(self, monitor):
        client = AsyncMock()
        client.get.side_effect = httpx.RequestError("Connection refused")
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        with patch("model_monitor.httpx.AsyncClient", return_value=client):
            models = await monitor.get_running_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_empty_response(self, monitor):
        with patch("model_monitor.httpx.AsyncClient", return_value=_mock_client({"models": []})):
            models = await monitor.get_available_models()

        assert models == []


class TestFormatModelReport:
    """Test format_model_report function."""

    @pytest.mark.asyncio
    async def test_report_with_models(self):
        health = {
            "available": [
                ModelInfo(name="llama3:8b", size=4661224448, modified_at="2024-01-15", digest="abc"),
            ],
            "loaded": [
                ModelInfo(name="llama3:8b", size=4661224448, modified_at="2024-01-15",
                          digest="abc", loaded=True, vram_bytes=4661224448,
                          expires_at="2024-01-15T11:30:00Z"),
            ],
            "summary": {"total_available": 1, "total_loaded": 1, "total_vram_bytes": 4661224448},
        }

        report = await format_model_report(health)

        assert "llama3:8b" in report
        assert "Available Models" in report
        assert "Loaded Models" in report
        assert "Summary" in report
        assert "4.34" in report  # 4661224448 / 1024^3 ≈ 4.34 GB

    @pytest.mark.asyncio
    async def test_report_empty_models(self):
        health = {
            "available": [],
            "loaded": [],
            "summary": {"total_available": 0, "total_loaded": 0, "total_vram_bytes": 0},
        }

        report = await format_model_report(health)

        assert "No available models" in report
        assert "No models currently loaded" in report
        assert "0 available" in report

    @pytest.mark.asyncio
    async def test_report_multiple_models(self):
        health = {
            "available": [
                ModelInfo(name="llama3:8b", size=4661224448, modified_at="2024-01-15", digest="a"),
                ModelInfo(name="mistral:7b", size=4000000000, modified_at="2024-01-14", digest="b"),
            ],
            "loaded": [
                ModelInfo(name="llama3:8b", size=4661224448, modified_at="2024-01-15",
                          digest="a", loaded=True, vram_bytes=4661224448, expires_at="2024-01-15T11:30:00Z"),
            ],
            "summary": {"total_available": 2, "total_loaded": 1, "total_vram_bytes": 4661224448},
        }

        report = await format_model_report(health)

        assert "llama3:8b" in report
        assert "mistral:7b" in report
        assert "2 available" in report
        assert "1 loaded" in report
