"""Tests for the backend config module."""

import pytest

from decisions_demo.config import (
    DEFAULT_DECISIONS_MODEL_GEMINI_API,
    DEFAULT_DECISIONS_MODEL_VERTEX,
    DEFAULT_TIER_MODELS,
    Backend,
    ConfigError,
    load_config,
)


def test_default_backend_is_gemini_api():
    config = load_config({"GEMINI_API_KEY": "test-key"})

    assert config.backend is Backend.GEMINI_API
    assert config.decisions_model == DEFAULT_DECISIONS_MODEL_GEMINI_API
    assert config.api_key == "test-key"


def test_gemini_api_without_key_raises_clear_error():
    with pytest.raises(ConfigError, match="GEMINI_API_KEY is not set"):
        load_config({})


def test_vertex_backend():
    config = load_config(
        {
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_CLOUD_PROJECT": "demo-project",
            "GOOGLE_CLOUD_LOCATION": "global",
        }
    )

    assert config.backend is Backend.VERTEX_AI
    assert config.decisions_model == DEFAULT_DECISIONS_MODEL_VERTEX
    assert config.project == "demo-project"
    assert config.location == "global"
    assert config.api_key is None


@pytest.mark.parametrize("value", ["1", "TRUE", "True", "yes"])
def test_vertex_flag_accepts_common_true_values(value):
    config = load_config({"GOOGLE_GENAI_USE_VERTEXAI": value, "GOOGLE_CLOUD_PROJECT": "p"})

    assert config.backend is Backend.VERTEX_AI


def test_vertex_location_defaults_to_global():
    config = load_config({"GOOGLE_GENAI_USE_VERTEXAI": "true", "GOOGLE_CLOUD_PROJECT": "p"})

    assert config.location == "global"


def test_vertex_without_project_raises_clear_error():
    with pytest.raises(ConfigError, match="GOOGLE_CLOUD_PROJECT is not set"):
        load_config({"GOOGLE_GENAI_USE_VERTEXAI": "true"})


def test_vertex_flag_false_uses_gemini_api():
    config = load_config({"GOOGLE_GENAI_USE_VERTEXAI": "false", "GEMINI_API_KEY": "k"})

    assert config.backend is Backend.GEMINI_API


def test_decisions_model_override():
    config = load_config({"GEMINI_API_KEY": "k", "DECISIONS_MODEL": "custom-decision"})

    assert config.decisions_model == "custom-decision"


def test_tier_model_overrides():
    config = load_config(
        {
            "GEMINI_API_KEY": "k",
            "MODEL_TIER_LITE": "lite-x",
            "MODEL_TIER_FLASH": "flash-x",
            "MODEL_TIER_PRO": "pro-x",
        }
    )

    assert config.tier_models == {"lite": "lite-x", "flash": "flash-x", "pro": "pro-x"}


def test_empty_override_uses_default():
    config = load_config({"GEMINI_API_KEY": "k", "DECISIONS_MODEL": ""})

    assert config.decisions_model == DEFAULT_DECISIONS_MODEL_GEMINI_API


def test_default_tier_models():
    config = load_config({"GEMINI_API_KEY": "k"})

    assert config.tier_models == DEFAULT_TIER_MODELS


def test_vertex_describe_names_project():
    config = load_config({"GOOGLE_GENAI_USE_VERTEXAI": "true", "GOOGLE_CLOUD_PROJECT": "p1"})

    assert "Vertex AI" in config.describe()
    assert "p1" in config.describe()


def test_describe_names_backend_and_model_but_not_key():
    config = load_config({"GEMINI_API_KEY": "secret-key-123"})

    text = config.describe()

    assert "Gemini Developer API" in text
    assert DEFAULT_DECISIONS_MODEL_GEMINI_API in text
    assert "secret-key-123" not in text
