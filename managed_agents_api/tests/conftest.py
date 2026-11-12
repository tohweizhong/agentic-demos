"""Shared test settings.

Unit tests must not call the network. The fixture below replaces the functions
that get real credentials or a real SDK client. A test that reaches them fails.
"""

import pytest

from managed_agents_demo import client, storage


def _blocked(*args, **kwargs):
    raise RuntimeError("Unit tests must not call the network. Use a fake client.")


@pytest.fixture(autouse=True)
def block_network(request, monkeypatch):
    if request.node.get_closest_marker("integration"):
        return
    monkeypatch.setattr(client, "default_token_provider", _blocked)
    monkeypatch.setattr(client, "make_genai_client", _blocked)
    monkeypatch.setattr(storage, "make_storage_client", _blocked)
