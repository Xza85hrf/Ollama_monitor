"""Alerting integration via webhooks."""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx


logger = logging.getLogger(__name__)


class AlertManager:
    """Manage alerts for monitoring failures."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        alert_on_failure: bool = True,
        alert_threshold: float = 0.95,
        min_failures: int = 3
    ):
        """
        Initialize AlertManager.

        Args:
            webhook_url: Webhook URL for sending alerts
            alert_on_failure: Whether to alert on failures
            alert_threshold: Success rate threshold for alerting (0.0-1.0)
            min_failures: Minimum number of failures before alerting
        """
        self.webhook_url = webhook_url
        self.alert_on_failure = alert_on_failure
        self.alert_threshold = alert_threshold
        self.min_failures = min_failures
        self.failure_counts: Dict[str, int] = {}
        self.total_checks: Dict[str, int] = {}
        self.enabled = webhook_url is not None

    async def send_alert(
        self,
        message: str,
        severity: str = "warning",
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send alert via webhook.

        Args:
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
            endpoint: Endpoint that triggered the alert
            details: Additional details

        Returns:
            True if alert was sent successfully, False otherwise
        """
        if not self.enabled or not self.webhook_url:
            logger.debug("Alerting disabled or webhook URL not configured")
            return False

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "severity": severity,
            "message": message,
            "service": "ollama-monitor",
        }

        if endpoint:
            payload["endpoint"] = endpoint

        if details:
            payload["details"] = details

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Alert sent successfully: {message}")
                    return True
                else:
                    logger.error(
                        f"Failed to send alert. Status: {response.status_code}, "
                        f"Response: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    def record_check(self, endpoint: str, success: bool) -> None:
        """
        Record endpoint check result.

        Args:
            endpoint: Endpoint name
            success: Whether the check was successful
        """
        if endpoint not in self.total_checks:
            self.total_checks[endpoint] = 0
            self.failure_counts[endpoint] = 0

        self.total_checks[endpoint] += 1
        if not success:
            self.failure_counts[endpoint] += 1

    async def check_and_alert(self, endpoint: str, success: bool, error: Optional[str] = None) -> None:
        """
        Check if alert should be sent and send if necessary.

        Args:
            endpoint: Endpoint name
            success: Whether the check was successful
            error: Error message if check failed
        """
        if not self.alert_on_failure:
            return

        self.record_check(endpoint, success)

        # Alert on immediate failure threshold
        if not success and self.failure_counts[endpoint] >= self.min_failures:
            consecutive_failures = self.failure_counts[endpoint]
            message = (
                f"Endpoint '{endpoint}' has failed {consecutive_failures} times consecutively"
            )

            details = {
                "consecutive_failures": consecutive_failures,
                "total_checks": self.total_checks[endpoint]
            }

            if error:
                details["last_error"] = error

            await self.send_alert(
                message=message,
                severity="error",
                endpoint=endpoint,
                details=details
            )

        # Alert on success rate threshold
        if self.total_checks[endpoint] >= 10:  # Minimum sample size
            success_rate = 1 - (self.failure_counts[endpoint] / self.total_checks[endpoint])

            if success_rate < self.alert_threshold:
                message = (
                    f"Endpoint '{endpoint}' success rate ({success_rate:.1%}) "
                    f"is below threshold ({self.alert_threshold:.1%})"
                )

                details = {
                    "success_rate": f"{success_rate:.1%}",
                    "threshold": f"{self.alert_threshold:.1%}",
                    "total_checks": self.total_checks[endpoint],
                    "failures": self.failure_counts[endpoint]
                }

                await self.send_alert(
                    message=message,
                    severity="warning",
                    endpoint=endpoint,
                    details=details
                )

        # Reset failure count on success
        if success:
            self.failure_counts[endpoint] = 0

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.failure_counts.clear()
        self.total_checks.clear()

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all endpoints.

        Returns:
            Dictionary with endpoint statistics
        """
        stats = {}
        for endpoint in self.total_checks:
            total = self.total_checks[endpoint]
            failures = self.failure_counts[endpoint]
            success_rate = 1 - (failures / total) if total > 0 else 1.0

            stats[endpoint] = {
                "total_checks": total,
                "failures": failures,
                "successes": total - failures,
                "success_rate": f"{success_rate:.1%}"
            }

        return stats
