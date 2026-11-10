"""Tests for the deploy config. These tests run offline."""

import config
import deploy


def _settings(tmp_path, monkeypatch, extra=""):
  for key in list(config.DEFAULTS) + ["PROJECT_ID", "STAGING_BUCKET"]:
    monkeypatch.delenv(key, raising=False)
  env_file = tmp_path / ".env"
  env_file.write_text("PROJECT_ID=p\nSTAGING_BUCKET=b\n" + extra)
  return config.load_settings(env_file)


def test_requirements_are_pinned():
  lines = deploy.requirements()
  assert "google-cloud-agentplatform[agent-engines,adk]==2.7.0" in lines
  assert "google-adk==2.14.0" in lines
  assert all("==" in line for line in lines)


def test_env_vars_turn_on_telemetry_without_message_content(tmp_path, monkeypatch):
  values = deploy.env_vars(_settings(tmp_path, monkeypatch))
  assert values["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] == "true"
  assert values["OTEL_SEMCONV_STABILITY_OPT_IN"] == "gen_ai_latest_experimental"
  assert values["MODEL"] == "gemini-3.5-flash"
  assert "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT" not in values


def test_env_vars_capture_message_content_when_turned_on(tmp_path, monkeypatch):
  settings = _settings(tmp_path, monkeypatch, "CAPTURE_MESSAGE_CONTENT=true\n")
  values = deploy.env_vars(settings)
  assert values["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] == "EVENT_ONLY"


def test_context_spec_sets_both_memory_bank_models(tmp_path, monkeypatch):
  spec = deploy.context_spec(_settings(tmp_path, monkeypatch))
  bank = spec["memory_bank_config"]
  assert bank["generation_config"]["model"].endswith(
      "/locations/asia-southeast1/publishers/google/models/gemini-3.5-flash"
  )
  assert bank["similarity_search_config"]["embedding_model"].endswith(
      "/models/text-embedding-005"
  )


def test_runtime_config_has_staging_bucket_and_agent_package(tmp_path, monkeypatch):
  cfg = deploy.runtime_config(_settings(tmp_path, monkeypatch))
  assert cfg["staging_bucket"] == "gs://b"
  assert cfg["extra_packages"] == ["agent"]
  assert cfg["display_name"] == "svcpack-agent"
  assert "memory_bank_config" in cfg["context_spec"]
