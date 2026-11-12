"""Tests for the terminal output module."""

import io

from rich.console import Console

from managed_agents_demo import console as out


def make_console() -> tuple[Console, io.StringIO]:
    buffer = io.StringIO()
    return Console(file=buffer, width=120, color_system=None), buffer


def test_mask_token_hides_bearer_value():
    masked = out.mask_secrets({"Authorization": "Bearer fake-token-value"})
    assert masked == {"Authorization": "Bearer ***"}


def test_mask_secrets_is_recursive_and_keeps_other_values():
    data = {
        "tools": [
            {
                "type": "mcp_server",
                "headers": {"Authorization": "Bearer secret-token", "X-Goog-User-Project": "p"},
            }
        ],
        "id": "demo-agent",
    }
    masked = out.mask_secrets(data)
    assert masked["tools"][0]["headers"]["Authorization"] == "Bearer ***"
    assert masked["tools"][0]["headers"]["X-Goog-User-Project"] == "p"
    assert masked["id"] == "demo-agent"
    # The input does not change.
    assert data["tools"][0]["headers"]["Authorization"] == "Bearer secret-token"


def test_mask_secrets_masks_value_without_bearer_prefix():
    assert out.mask_secrets({"authorization": "abc"}) == {"authorization": "***"}


def test_blocks_print_in_order_with_titles():
    console, buffer = make_console()
    out.request(console, "POST /agents", {"id": "demo-a", "headers": {"Authorization": "Bearer x"}})
    out.response(console, {"name": "operations/1"})
    out.result(console, "Agent is ready.")
    text = buffer.getvalue()
    assert text.index("Request") < text.index("Response") < text.index("Result")
    assert "POST /agents" in text
    assert "demo-a" in text
    assert "Bearer x" not in text
    assert "Agent is ready." in text


def test_error_prints_status_and_message():
    console, buffer = make_console()
    out.error(console, "Permission denied.", status=403)
    text = buffer.getvalue()
    assert "403" in text
    assert "Permission denied." in text


def test_elapsed_formats_seconds():
    assert out.format_elapsed(0.04) == "0.0 s"
    assert out.format_elapsed(142.26) == "142.3 s"
