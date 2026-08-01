import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import ConfigurationError, Settings


def test_settings_read_m5_environment_values() -> None:
    settings = Settings.from_environment(
        {
            "M5_ALLOWED_ORIGINS": "https://m5.internal, https://vscode.dev",
            "M5_OLLAMA_BASE_URL": "http://ollama:11434",
            "M5_OLLAMA_MODEL": "approved-model",
            "M5_REQUEST_TIMEOUT_SECONDS": "15",
            "M5_QDRANT_HOST": "qdrant",
            "M5_QDRANT_PORT": "6333",
            "M5_WORKSPACE_ROOT": ".",
        }
    )

    assert settings.allowed_origins == ("https://m5.internal", "https://vscode.dev")
    assert settings.ollama_base_url == "http://ollama:11434"
    assert settings.request_timeout_seconds == 15.0
    assert settings.qdrant_host == "qdrant"


def test_settings_reject_wildcard_cors_origin() -> None:
    with pytest.raises(ConfigurationError, match="must not include"):
        Settings.from_environment({"M5_ALLOWED_ORIGINS": "*"})


def test_settings_use_the_approved_groq_model_by_default() -> None:
    settings = Settings.from_environment({})

    assert settings.groq_model == "llama-3.3-70b-versatile"
