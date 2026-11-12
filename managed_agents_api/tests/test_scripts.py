"""Tests for the thin scripts in `scripts/`."""

import importlib.util
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_access_check_script_stops_without_project(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)  # No .env file in this folder.
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    script = load_script("00_access_check.py")
    assert script.main() == 1
    assert "GOOGLE_CLOUD_PROJECT is not set" in capsys.readouterr().out


def test_network_guard_stops_a_real_call(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("GOOGLE_CLOUD_PROJECT=guard-test\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    script = load_script("00_access_check.py")
    with pytest.raises(RuntimeError, match="must not call the network"):
        script.main()


def test_lifecycle_script_stops_without_project(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    assert load_script("01_lifecycle.py").main() == 1
    assert "GOOGLE_CLOUD_PROJECT is not set" in capsys.readouterr().out


def test_setup_bucket_script_stops_without_project(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    assert load_script("00b_setup_bucket.py").main() == 1
    assert "GOOGLE_CLOUD_PROJECT is not set" in capsys.readouterr().out
