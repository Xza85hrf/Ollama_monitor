"""Integration tests for new features."""
import pytest
import tempfile
import os
import logging
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from config_validator import validate_config, EndpointConfigModel, MonitorConfigModel
from logger_config import setup_logging, JSONFormatter
from alerting import AlertManager
from report_generator import (
    generate_text_report,
    generate_json_report,
    generate_csv_report,
    generate_html_report,
)


class TestConfigValidator:
    """Test configuration validation."""

    def test_valid_config(self):
        """Test validation with valid configuration."""
        config_dict = {
            "base_url": "http://localhost:11434",
            "timeout": 30,
            "endpoints": {
                "/": {
                    "path": "/",
                    "method": "GET",
                    "expected_status": 200
                }
            }
        }

        validated = validate_config(config_dict)
        assert isinstance(validated, MonitorConfigModel)
        assert str(validated.base_url) == "http://localhost:11434/"
        assert validated.timeout == 30
        assert "/" in validated.endpoints

    def test_invalid_method(self):
        """Test validation fails with invalid HTTP method."""
        config_dict = {
            "base_url": "http://localhost:11434",
            "timeout": 30,
            "endpoints": {
                "/": {
                    "path": "/",
                    "method": "INVALID",
                    "expected_status": 200
                }
            }
        }

        with pytest.raises(Exception):
            validate_config(config_dict)

    def test_alerting_validation(self):
        """Test alerting configuration validation."""
        config_dict = {
            "base_url": "http://localhost:11434",
            "timeout": 30,
            "endpoints": {
                "/": {
                    "path": "/",
                    "method": "GET",
                    "expected_status": 200
                }
            },
            "alerting": {
                "enabled": True,
                "webhook_url": "https://hooks.slack.com/services/test",
                "alert_threshold": 0.95
            }
        }

        validated = validate_config(config_dict)
        assert validated.alerting is not None
        assert validated.alerting.enabled is True
        assert validated.alerting.alert_threshold == 0.95


class TestLogging:
    """Test structured logging."""

    def test_json_formatter(self):
        """Test JSON formatter produces valid JSON."""
        import logging
        import json

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        # Should be valid JSON
        data = json.loads(formatted)

        assert "timestamp" in data
        assert "level" in data
        assert "message" in data
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"

    def test_setup_logging_text(self):
        """Test text logging setup."""
        setup_logging(log_level="INFO", json_format=False)
        logger = logging.getLogger("test")

        # Should not raise exception
        logger.info("Test message")

    def test_setup_logging_json(self):
        """Test JSON logging setup."""
        setup_logging(log_level="INFO", json_format=True)
        logger = logging.getLogger("test")

        # Should not raise exception
        logger.info("Test message")


class TestAlertManager:
    """Test alerting functionality."""

    def test_init(self):
        """Test AlertManager initialization."""
        manager = AlertManager(
            webhook_url="https://example.com/webhook",
            alert_threshold=0.95,
            min_failures=3
        )

        assert manager.enabled is True
        assert manager.alert_threshold == 0.95
        assert manager.min_failures == 3

    def test_record_check(self):
        """Test recording check results."""
        manager = AlertManager(webhook_url="https://example.com/webhook")

        manager.record_check("test_endpoint", True)
        assert manager.total_checks["test_endpoint"] == 1
        assert manager.failure_counts["test_endpoint"] == 0

        manager.record_check("test_endpoint", False)
        assert manager.total_checks["test_endpoint"] == 2
        assert manager.failure_counts["test_endpoint"] == 1

    def test_get_stats(self):
        """Test statistics retrieval."""
        manager = AlertManager(webhook_url="https://example.com/webhook")

        manager.record_check("ep1", True)
        manager.record_check("ep1", False)
        manager.record_check("ep2", True)

        stats = manager.get_stats()
        assert "ep1" in stats
        assert "ep2" in stats
        assert stats["ep1"]["total_checks"] == 2
        assert stats["ep1"]["failures"] == 1

    @pytest.mark.asyncio
    async def test_send_alert_disabled(self):
        """Test alert sending when disabled."""
        manager = AlertManager(webhook_url=None)

        result = await manager.send_alert("Test alert")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_success(self):
        """Test successful alert sending."""
        manager = AlertManager(webhook_url="https://example.com/webhook")

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = await manager.send_alert("Test alert", severity="warning")
            assert result is True


class TestReportGeneration:
    """Test report generation in multiple formats."""

    @pytest.fixture
    def sample_results(self):
        """Sample check results."""
        return [
            (0.123, 200),  # Success
            (0.456, 500),  # Failure
            Exception("Connection error"),  # Error
        ]

    @pytest.fixture
    def sample_endpoints(self):
        """Sample endpoints."""
        from ollama_monitor import EndpointConfig
        return {
            "/": EndpointConfig(path="/", method="GET"),
            "/api": EndpointConfig(path="/api", method="POST"),
            "/status": EndpointConfig(path="/status", method="GET"),
        }

    @pytest.mark.asyncio
    async def test_text_report(self, sample_results, sample_endpoints, tmp_path):
        """Test text report generation."""
        output_file = tmp_path / "report.txt"

        await generate_text_report(sample_results, str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "Ollama Monitor Report" in content
        assert "Status Code: 200" in content

    @pytest.mark.asyncio
    async def test_json_report(self, sample_results, sample_endpoints, tmp_path):
        """Test JSON report generation."""
        import json
        output_file = tmp_path / "report.json"

        await generate_json_report(sample_results, sample_endpoints, str(output_file))

        assert output_file.exists()
        content = json.loads(output_file.read_text())
        assert "summary" in content
        assert "endpoints" in content
        assert content["summary"]["total_endpoints"] == 3

    @pytest.mark.asyncio
    async def test_csv_report(self, sample_results, sample_endpoints, tmp_path):
        """Test CSV report generation."""
        output_file = tmp_path / "report.csv"

        await generate_csv_report(sample_results, sample_endpoints, str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "Endpoint,Status,Status Code" in content

    @pytest.mark.asyncio
    async def test_html_report(self, sample_results, sample_endpoints, tmp_path):
        """Test HTML report generation."""
        output_file = tmp_path / "report.html"

        await generate_html_report(sample_results, sample_endpoints, str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "<!DOCTYPE html>" in content
        assert "Ollama Monitor Report" in content
        assert "success" in content.lower() or "failed" in content.lower()
