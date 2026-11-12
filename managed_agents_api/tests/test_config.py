"""Tests for the configuration module."""

import pytest

from managed_agents_demo import config


def test_load_reads_project_from_environment(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    settings = config.load(dotenv=False)
    assert settings.project == "test-project"
    assert settings.location == "global"


def test_load_strips_spaces(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "  test-project  ")
    assert config.load(dotenv=False).project == "test-project"


@pytest.mark.parametrize("value", [None, "", "your-project-id"])
def test_load_without_project_states_the_fix(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    else:
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", value)
    with pytest.raises(config.ConfigError) as excinfo:
        config.load(dotenv=False)
    message = str(excinfo.value)
    assert "GOOGLE_CLOUD_PROJECT is not set" in message
    assert "Copy .env.example to .env" in message


def test_parent_and_base_url(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    settings = config.load(dotenv=False)
    assert settings.parent == "projects/test-project/locations/global"
    assert settings.base_url == (
        "https://aiplatform.googleapis.com/v1beta1/projects/test-project/locations/global"
    )


def test_constants():
    assert config.BASE_AGENT == "antigravity-preview-05-2026"
    assert config.AGENT_ID_PREFIX == "demo-"


def test_load_reads_env_file_in_current_folder(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    (tmp_path / ".env").write_text("GOOGLE_CLOUD_PROJECT=from-env-file\n")
    monkeypatch.chdir(tmp_path)
    assert config.load().project == "from-env-file"
