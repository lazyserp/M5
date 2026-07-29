"""Validated runtime configuration for the M5 backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


class ConfigurationError(ValueError):
    """Raised when an M5 configuration value is unsafe or invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings supplied solely through the environment."""

    allowed_origins: tuple[str, ...]
    ollama_base_url: str
    ollama_model: str
    request_timeout_seconds: float
    qdrant_host: str
    qdrant_port: int
    workspace_root: Path
    nvidia_api_key: str | None
    nvidia_model: str

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "Settings":
        environment = environment or os.environ
        allowed_origins = tuple(
            origin.strip()
            for origin in environment.get("M5_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )
        if "*" in allowed_origins:
            raise ConfigurationError("M5_ALLOWED_ORIGINS must not include '*'.")

        ollama_base_url = environment.get("M5_OLLAMA_BASE_URL", "http://localhost:11434")
        parsed_url = urlparse(ollama_base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ConfigurationError("M5_OLLAMA_BASE_URL must be an absolute HTTP(S) URL.")

        timeout = _positive_float(
            environment.get("M5_REQUEST_TIMEOUT_SECONDS", "300"),
            "M5_REQUEST_TIMEOUT_SECONDS",
        )
        qdrant_port = _port_number(environment.get("M5_QDRANT_PORT", "6333"))
        workspace_root = Path(environment.get("M5_WORKSPACE_ROOT", ".")).resolve()
        return cls(
            allowed_origins=allowed_origins,
            ollama_base_url=ollama_base_url.rstrip("/"),
            ollama_model=environment.get("M5_OLLAMA_MODEL", "qwen2.5-coder:1.5b"),
            request_timeout_seconds=timeout,
            qdrant_host=environment.get("M5_QDRANT_HOST", "localhost"),
            qdrant_port=qdrant_port,
            workspace_root=workspace_root,
            nvidia_api_key=environment.get("NVIDIA_API_KEY") or None,
            nvidia_model=environment.get(
                "NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b"
            ),
        )


def _positive_float(value: str, name: str) -> float:
    try:
        converted = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a number.") from error
    if converted <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return converted


def _port_number(value: str) -> int:
    try:
        port = int(value)
    except ValueError as error:
        raise ConfigurationError("M5_QDRANT_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise ConfigurationError("M5_QDRANT_PORT must be between 1 and 65535.")
    return port
