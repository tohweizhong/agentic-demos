"""Tests for the Skill Registry helpers."""

import base64
import io
import json
import zipfile
from types import SimpleNamespace

import httpx2 as httpx
from rich.console import Console

from managed_agents_demo import client, skills
from managed_agents_demo.config import Settings

SETTINGS = Settings(project="test-project")
BASE = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/test-project/locations/us-central1"


def make_rest(handler):
    calls = []

    def recording(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        calls.append((request.method, str(request.url), body))
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(recording))
    return client.RestClient(SETTINGS, token_provider=lambda: "t", http=http), calls


def test_rest_client_accepts_absolute_url():
    rest, calls = make_rest(lambda request: httpx.Response(200, json={}))
    rest.request("GET", "https://example.test/v1/x")
    assert calls[0][1] == "https://example.test/v1/x"


def test_zip_skill_has_skill_md_at_root():
    data = skills.zip_skill(skills.SKILL_FOLDER)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.namelist() == ["SKILL.md"]
        assert archive.read("SKILL.md").decode().startswith("---\nname: sales-chart-style")


def test_skill_resource_names():
    assert skills.skill_url("p") == (
        "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/p/locations/us-central1/skills"
    )
    assert skills.skill_resource("p") == "projects/p/locations/us-central1/skills/sales-chart-style"


def test_publish_creates_when_missing():
    def handler(request):
        if request.method == "GET" and request.url.path.endswith("/skills/sales-chart-style"):
            return httpx.Response(404, json={"error": {"code": 404, "message": "not found"}})
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "name": "projects/1/locations/us-central1/skills/sales-chart-style/operations/9"
                },
            )
        return httpx.Response(200, json={"done": True, "response": {}})

    rest, calls = make_rest(handler)
    result = skills.publish(rest, "test-project", sleep=lambda s: None)
    assert result == "created"
    method, url, body = calls[1]
    assert method == "POST"
    assert url == f"{BASE}/skills?skillId=sales-chart-style"
    assert body["displayName"] == "Sales chart style"
    archive = zipfile.ZipFile(io.BytesIO(base64.b64decode(body["zippedFilesystem"])))
    assert archive.namelist() == ["SKILL.md"]
    assert calls[2][1] == (
        "https://us-central1-aiplatform.googleapis.com/v1beta1/"
        "projects/1/locations/us-central1/skills/sales-chart-style/operations/9"
    )


def test_publish_updates_when_present():
    def handler(request):
        if request.method == "GET" and request.url.path.endswith("/skills/sales-chart-style"):
            return httpx.Response(200, json={"name": "x", "state": "ACTIVE"})
        if request.method == "PATCH":
            return httpx.Response(
                200, json={"name": "projects/1/locations/us-central1/operations/8", "done": True}
            )
        raise AssertionError("unexpected call")

    rest, calls = make_rest(handler)
    assert skills.publish(rest, "test-project", sleep=lambda s: None) == "updated"
    method, url, body = calls[1]
    assert method == "PATCH"
    assert (
        url
        == f"{BASE}/skills/sales-chart-style?updateMask="
        + "displayName%2Cdescription%2CzippedFilesystem"
    )
    assert set(body) == {"displayName", "description", "zippedFilesystem"}


def test_delete_skill():
    rest, calls = make_rest(lambda request: httpx.Response(200, json={"done": True}))
    skills.delete(rest, "test-project", sleep=lambda s: None)
    assert calls[0][:2] == ("DELETE", f"{BASE}/skills/sales-chart-style")


def test_skill_agent_body_has_bucket_and_registry_sources():
    body = skills.build_skill_agent_body(bucket="b", project="p")
    assert body["id"] == "demo-skill-analyst"
    sources = body["base_environment"]["sources"]
    assert sources[0] == {"type": "gcs", "source": "gs://b/agent", "target": ".agent"}
    assert sources[1] == {
        "type": "skill_registry",
        "source": "projects/p/locations/us-central1/skills/sales-chart-style",
        "target": "skills",
    }
    assert "/workspace/skills/" in body["system_instruction"]
    assert body["base_environment"]["network"] == {"allowlist": [{"domain": "*"}]}


def test_chart_name_check():
    assert skills.follows_skill_name(["agent/output/chart_revenue_by_region.png"])
    assert not skills.follows_skill_name(["agent/output/revenue_by_region_quarter.png"])


def test_run_publishes_creates_agent_and_checks_chart(monkeypatch):
    rest, calls = make_rest(lambda request: httpx.Response(200, json={"done": True}))
    monkeypatch.setattr(skills, "publish", lambda rest, project, **kw: "updated")
    events = [
        {
            "event_type": "step.start",
            "index": 0,
            "step": {"type": "function_call", "name": "view_file"},
        },
        {
            "event_type": "interaction.completed",
            "interaction": {"id": "i", "status": "completed", "environment_id": "e"},
        },
    ]
    sdk = SimpleNamespace(interactions=SimpleNamespace(create=lambda **kw: iter(events)))
    storage = SimpleNamespace(
        list_blobs=lambda bucket, prefix=None: [
            SimpleNamespace(name="agent/output/chart_revenue_by_region.png", size=10)
        ]
    )
    buffer = io.StringIO()
    console = Console(file=buffer, width=160, color_system=None)
    code = skills.run(rest, sdk, storage, console, SETTINGS, sleep=lambda s: None)
    assert code == 0
    assert calls[0][0] == "POST"  # create the skill agent
    assert "chart_revenue_by_region.png" in buffer.getvalue()
    assert "follows the skill" in buffer.getvalue()
