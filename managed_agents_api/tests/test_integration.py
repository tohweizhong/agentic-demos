"""Integration test against the real API.

The test runs only when RUN_INTEGRATION=1 and GOOGLE_CLOUD_PROJECT are set. It needs
the demo bucket (run scripts/00b_setup_bucket.py first). It creates one agent, sends
one interaction, and deletes the agent, also when an assertion fails.
"""

import os

import pytest

from managed_agents_demo import agent_config, client, config, interactions, lifecycle

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1",
        reason="Set RUN_INTEGRATION=1 to call the real API.",
    ),
]

AGENT_ID = "demo-integration-test"


def test_create_interact_delete():
    settings = config.load()
    rest = client.RestClient(settings)
    sdk = client.make_genai_client(settings)
    body = agent_config.build_agent_body(bucket=settings.bucket, agent_id=AGENT_ID)
    operation = lifecycle.create(rest, body)
    try:
        client.wait_for_operation(rest, client.operation_name_of(operation))
        assert lifecycle.agent_id_of(lifecycle.get(sdk, AGENT_ID)) == AGENT_ID
        request = interactions.build_request(
            AGENT_ID,
            "Count the data rows in /workspace/.agent/data/sales.csv, without the header row. "
            "Answer with one number only.",
        )
        summary = interactions.consume(interactions.start(sdk, request))
        assert summary.status == "completed"
        assert summary.environment_id
        assert "144" in summary.final_text
    finally:
        deleted = lifecycle.delete(rest, AGENT_ID)
        if deleted.get("name") and not deleted.get("done"):
            client.wait_for_operation(rest, deleted["name"])
