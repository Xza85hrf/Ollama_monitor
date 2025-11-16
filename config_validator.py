"""Configuration validation using Pydantic models."""
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict


class EndpointConfigModel(BaseModel):
    """Pydantic model for endpoint configuration validation."""

    path: str = Field(..., description="Endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    expected_status: int = Field(default=200, ge=100, le=599, description="Expected HTTP status code")
    expected_content: Optional[str] = Field(default=None, description="Expected content in response")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers")
    body: Optional[Dict[str, Any]] = Field(default=None, description="Request body for POST/PUT")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        allowed = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if v.upper() not in allowed:
            raise ValueError(f'Method must be one of {allowed}')
        return v.upper()


class AlertConfigModel(BaseModel):
    """Pydantic model for alert configuration validation."""

    enabled: bool = Field(default=False, description="Enable alerting")
    webhook_url: Optional[HttpUrl] = Field(default=None, description="Webhook URL for alerts")
    alert_on_failure: bool = Field(default=True, description="Alert on endpoint failures")
    alert_threshold: float = Field(default=0.95, ge=0.0, le=1.0, description="Success rate threshold")
    min_failures: int = Field(default=3, ge=1, description="Minimum failures before alerting")

    @field_validator('webhook_url')
    @classmethod
    def validate_webhook_url(cls, v: Optional[HttpUrl], info) -> Optional[HttpUrl]:
        """Validate webhook URL is provided if alerting is enabled."""
        if info.data.get('enabled') and not v:
            raise ValueError('webhook_url is required when alerting is enabled')
        return v


class MonitorConfigModel(BaseModel):
    """Pydantic model for main configuration validation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "base_url": "http://localhost:11434",
                "timeout": 30,
                "endpoints": {
                    "/": {
                        "path": "/",
                        "method": "GET",
                        "expected_status": 200,
                        "expected_content": "Ollama is running"
                    }
                },
                "alerting": {
                    "enabled": True,
                    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
                    "alert_on_failure": True,
                    "alert_threshold": 0.95
                }
            }
        }
    )

    base_url: HttpUrl = Field(..., description="Base URL of the Ollama server")
    timeout: int = Field(default=10, ge=1, le=300, description="Request timeout in seconds")
    endpoints: Dict[str, EndpointConfigModel] = Field(..., description="Endpoints to monitor")
    alerting: Optional[AlertConfigModel] = Field(default=None, description="Alert configuration")


def validate_config(config_dict: Dict[str, Any]) -> MonitorConfigModel:
    """
    Validate configuration dictionary using Pydantic.

    Args:
        config_dict: Configuration dictionary loaded from YAML

    Returns:
        Validated MonitorConfigModel instance

    Raises:
        ValidationError: If configuration is invalid
    """
    # Convert endpoints to EndpointConfigModel instances
    if 'endpoints' in config_dict:
        endpoints = {}
        for path, endpoint_config in config_dict['endpoints'].items():
            endpoints[path] = EndpointConfigModel(**endpoint_config)
        config_dict['endpoints'] = endpoints

    # Convert alerting config if present
    if 'alerting' in config_dict and config_dict['alerting']:
        config_dict['alerting'] = AlertConfigModel(**config_dict['alerting'])

    return MonitorConfigModel(**config_dict)
