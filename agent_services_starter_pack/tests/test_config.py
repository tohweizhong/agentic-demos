"""Tests for the settings helper."""

import pytest

import config


def test_read_env_file_reads_values_and_skips_comments(tmp_path):
  env_file = tmp_path / ".env"
  env_file.write_text(
      "# A comment\n"
      "PROJECT_ID=my-project\n"
      "\n"
      'REGION="asia-southeast1"\n'
      "EMPTY=\n"
  )
  values = config.read_env_file(env_file)
  assert values == {
      "PROJECT_ID": "my-project",
      "REGION": "asia-southeast1",
      "EMPTY": "",
  }


def test_read_env_file_returns_empty_dict_when_file_is_missing(tmp_path):
  assert config.read_env_file(tmp_path / "missing.env") == {}


def test_set_env_value_replaces_an_existing_key(tmp_path):
  env_file = tmp_path / ".env"
  env_file.write_text("PROJECT_ID=p\nAGENT_RUNTIME_NAME=old\n")
  config.set_env_value(env_file, "AGENT_RUNTIME_NAME", "new")
  assert env_file.read_text() == "PROJECT_ID=p\nAGENT_RUNTIME_NAME=new\n"


def test_set_env_value_adds_a_new_key(tmp_path):
  env_file = tmp_path / ".env"
  env_file.write_text("PROJECT_ID=p")
  config.set_env_value(env_file, "AGENT_RUNTIME_NAME", "name")
  assert env_file.read_text() == "PROJECT_ID=p\nAGENT_RUNTIME_NAME=name\n"


def test_load_settings_uses_defaults_and_env_file(tmp_path, monkeypatch):
  for key in config.DEFAULTS:
    monkeypatch.delenv(key, raising=False)
  monkeypatch.delenv("PROJECT_ID", raising=False)
  env_file = tmp_path / ".env"
  env_file.write_text("PROJECT_ID=my-project\nSTAGING_BUCKET=my-bucket\n")
  settings = config.load_settings(env_file)
  assert settings.project_id == "my-project"
  assert settings.region == "asia-southeast1"
  assert settings.staging_bucket_uri == "gs://my-bucket"
  assert settings.model == "gemini-3.5-flash"


def test_load_settings_prefers_process_environment(tmp_path, monkeypatch):
  env_file = tmp_path / ".env"
  env_file.write_text("PROJECT_ID=from-file\nSTAGING_BUCKET=b\n")
  monkeypatch.setenv("PROJECT_ID", "from-env")
  assert config.load_settings(env_file).project_id == "from-env"


def test_load_settings_fails_when_project_is_missing(tmp_path, monkeypatch):
  monkeypatch.delenv("PROJECT_ID", raising=False)
  env_file = tmp_path / ".env"
  env_file.write_text("STAGING_BUCKET=b\n")
  with pytest.raises(config.SettingsError, match="PROJECT_ID"):
    config.load_settings(env_file)


def test_model_resource_names(tmp_path, monkeypatch):
  for key in config.DEFAULTS:
    monkeypatch.delenv(key, raising=False)
  monkeypatch.delenv("PROJECT_ID", raising=False)
  env_file = tmp_path / ".env"
  env_file.write_text(
      "PROJECT_ID=p\nSTAGING_BUCKET=b\nEMBEDDING_LOCATION=us-central1\n"
  )
  settings = config.load_settings(env_file)
  assert settings.generation_model_resource == (
      "projects/p/locations/asia-southeast1/publishers/google/models/"
      "gemini-3.5-flash"
  )
  assert settings.embedding_model_resource == (
      "projects/p/locations/us-central1/publishers/google/models/"
      "text-embedding-005"
  )


def test_runtime_id_is_the_last_part_of_the_name(tmp_path, monkeypatch):
  monkeypatch.delenv("PROJECT_ID", raising=False)
  monkeypatch.delenv("AGENT_RUNTIME_NAME", raising=False)
  env_file = tmp_path / ".env"
  env_file.write_text(
      "PROJECT_ID=p\nSTAGING_BUCKET=b\n"
      "AGENT_RUNTIME_NAME=projects/1/locations/asia-southeast1/"
      "reasoningEngines/42\n"
  )
  settings = config.load_settings(env_file)
  assert settings.runtime_id == "42"


def test_require_runtime_name_fails_before_deploy(tmp_path, monkeypatch):
  monkeypatch.delenv("PROJECT_ID", raising=False)
  monkeypatch.delenv("AGENT_RUNTIME_NAME", raising=False)
  env_file = tmp_path / ".env"
  env_file.write_text("PROJECT_ID=p\nSTAGING_BUCKET=b\n")
  settings = config.load_settings(env_file)
  with pytest.raises(config.SettingsError, match="deploy.py"):
    settings.require_runtime_name()
