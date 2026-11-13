"""Tests for the agent configuration."""

import pytest

from managed_agents_demo import agent_config, data
from managed_agents_demo.config import BASE_AGENT


def test_body_has_base_agent_and_tools():
    body = agent_config.build_agent_body(bucket="b")
    assert body["id"] == "demo-data-analyst"
    assert body["base_agent"] == BASE_AGENT
    assert {"type": "code_execution"} in body["tools"]
    assert {"type": "filesystem"} in body["tools"]
    assert body["base_environment"]["type"] == "remote"


def test_body_mounts_bucket_prefix_at_agent_folder():
    sources = agent_config.build_agent_body(bucket="my-bucket")["base_environment"]["sources"]
    assert sources == [{"type": "gcs", "source": "gs://my-bucket/agent", "target": ".agent"}]


def test_system_instruction_points_to_agents_md():
    body = agent_config.build_agent_body(bucket="b")
    assert "/workspace/.agent/AGENTS.md" in body["system_instruction"]


def test_network_allowlist_is_all_domains():
    # The Preview API needs an allowlist when a data source is set, and it accepts only "*".
    network = agent_config.build_agent_body(bucket="b")["base_environment"]["network"]
    assert network == {"allowlist": [{"domain": "*"}]}


def test_agent_id_must_use_demo_prefix():
    with pytest.raises(ValueError, match="demo-"):
        agent_config.build_agent_body(bucket="b", agent_id="analyst")


def test_agent_id_rules():
    for bad in ["demo-", "demo-Upper", "demo-end-", "demo-" + "a" * 60]:
        with pytest.raises(ValueError):
            agent_config.build_agent_body(bucket="b", agent_id=bad)
    assert agent_config.build_agent_body(bucket="b", agent_id="demo-a1")["id"] == "demo-a1"


def test_bucket_files_have_paths_and_content():
    files = agent_config.bucket_files()
    assert list(files) == [
        "agent/AGENTS.md",
        "agent/skills/report-writer/SKILL.md",
        "agent/data/sales.csv",
    ]
    assert files["agent/data/sales.csv"] == data.make_sales_csv()
    assert files["agent/skills/report-writer/SKILL.md"].startswith("---\nname: report-writer")
    assert "/workspace/.agent/data/sales.csv" in files["agent/AGENTS.md"]


def test_load_asset_reads_file():
    assert "report-writer" in agent_config.load_asset("report-writer/SKILL.md")


def test_no_agents_md_file_in_assets():
    # A file named AGENTS.md gives instructions to coding assistants that open the folder.
    # The analyst instructions use another local name and become AGENTS.md in the bucket.
    assert not (agent_config.ASSETS / "AGENTS.md").exists()
    assert agent_config.bucket_files()["agent/AGENTS.md"].startswith("# Data analyst agent")
