"""Model-level health monitoring for Ollama servers."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about an Ollama model."""

    name: str
    size: int
    modified_at: str
    digest: str
    loaded: bool = False
    vram_bytes: Optional[int] = None
    expires_at: Optional[str] = None


class ModelMonitor:
    """Monitor Ollama model availability and resource usage."""

    def __init__(self, base_url: str, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_available_models(self) -> list[ModelInfo]:
        """Fetch all downloaded models via /api/tags."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            return [
                ModelInfo(
                    name=m.get("name", ""),
                    size=m.get("size", 0),
                    modified_at=m.get("modified_at", ""),
                    digest=m.get("digest", ""),
                )
                for m in data.get("models", [])
            ]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching available models: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching available models: {e}")
        except ValueError as e:
            logger.error(f"JSON decode error fetching available models: {e}")

        return []

    async def get_running_models(self) -> list[ModelInfo]:
        """Fetch currently loaded models via /api/ps."""
        url = f"{self.base_url}/api/ps"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            return [
                ModelInfo(
                    name=m.get("name", ""),
                    size=m.get("size", 0),
                    modified_at=m.get("modified_at", ""),
                    digest=m.get("digest", ""),
                    loaded=True,
                    vram_bytes=m.get("size_vram"),
                    expires_at=m.get("expires_at"),
                )
                for m in data.get("models", [])
            ]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching running models: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching running models: {e}")
        except ValueError as e:
            logger.error(f"JSON decode error fetching running models: {e}")

        return []

    async def get_model_health(self) -> dict:
        """Get combined model health: available + loaded + summary."""
        available = await self.get_available_models()
        loaded = await self.get_running_models()

        total_vram = sum(m.vram_bytes for m in loaded if m.vram_bytes is not None)

        return {
            "available": available,
            "loaded": loaded,
            "summary": {
                "total_available": len(available),
                "total_loaded": len(loaded),
                "total_vram_bytes": total_vram,
            },
        }


async def format_model_report(health: dict) -> str:
    """Format model health data as a human-readable report."""
    lines: list[str] = []

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"Model Health Report - {timestamp}")
    lines.append("=" * 60)

    available = health.get("available", [])
    lines.append("Available Models:")
    if available:
        lines.append(f"  {'Name':<30} {'Size (GB)':<12} {'Modified'}")
        lines.append(f"  {'-' * 30} {'-' * 12} {'-' * 25}")
        for m in available:
            size_gb = m.size / (1024**3)
            lines.append(f"  {m.name:<30} {size_gb:<12.2f} {m.modified_at}")
    else:
        lines.append("  No available models found.")

    lines.append("")

    loaded = health.get("loaded", [])
    lines.append("Loaded Models:")
    if loaded:
        lines.append(f"  {'Name':<30} {'VRAM (GB)':<12} {'Expires'}")
        lines.append(f"  {'-' * 30} {'-' * 12} {'-' * 25}")
        for m in loaded:
            vram_gb = (m.vram_bytes or 0) / (1024**3)
            expires = m.expires_at or "N/A"
            lines.append(f"  {m.name:<30} {vram_gb:<12.2f} {expires}")
    else:
        lines.append("  No models currently loaded.")

    lines.append("=" * 60)
    summary = health.get("summary", {})
    total_vram_gb = summary.get("total_vram_bytes", 0) / (1024**3)
    lines.append(
        f"Summary: {summary.get('total_available', 0)} available, "
        f"{summary.get('total_loaded', 0)} loaded, "
        f"{total_vram_gb:.2f} GB VRAM in use"
    )

    return "\n".join(lines)
