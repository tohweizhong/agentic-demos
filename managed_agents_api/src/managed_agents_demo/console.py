"""Terminal output for the demo scripts.

Every script prints three blocks in this order: the request, the response, and
the result. The functions mask every authorization value before they print it.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

_SECRET_KEYS = {"authorization"}


def mask_secrets(data: Any) -> Any:
    """Return a copy of `data` with every authorization value masked."""
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if isinstance(key, str) and key.lower() in _SECRET_KEYS and isinstance(value, str):
                masked[key] = "Bearer ***" if value.startswith("Bearer ") else "***"
            else:
                masked[key] = mask_secrets(value)
        return masked
    if isinstance(data, list):
        return [mask_secrets(item) for item in data]
    return data


def _json(data: Any) -> Syntax:
    text = json.dumps(mask_secrets(data), indent=2, ensure_ascii=False, default=str)
    return Syntax(text, "json", word_wrap=True, theme="ansi_dark")


def request(console: Console, call: str, body: Any | None = None) -> None:
    """Print the request block: the HTTP call and the body."""
    content: Any = call if body is None else _json(body)
    title = "Request" if body is None else f"Request: {call}"
    console.print(Panel(content, title=title, title_align="left", border_style="cyan"))


def response(console: Console, body: Any) -> None:
    """Print the response block."""
    content: Any = body if isinstance(body, str) else _json(body)
    console.print(Panel(content, title="Response", title_align="left", border_style="magenta"))


def result(console: Console, text: str) -> None:
    """Print the result block."""
    console.print(Panel(text, title="Result", title_align="left", border_style="green"))


def error(console: Console, message: str, status: int | None = None) -> None:
    """Print an error. Include the HTTP status code if there is one."""
    title = "Error" if status is None else f"Error: HTTP {status}"
    console.print(Panel(message, title=title, title_align="left", border_style="red"))


def format_elapsed(seconds: float) -> str:
    """Return the elapsed time with one decimal place, for example `142.3 s`."""
    return f"{seconds:.1f} s"
