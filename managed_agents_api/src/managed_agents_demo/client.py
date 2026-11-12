"""Clients for the Managed Agents API.

The demo uses two clients:

- The `google-genai` SDK client, for `client.agents` and `client.interactions`.
- A small REST client, for the calls that the SDK does not have. The SDK has no
  `update` method, and its `create` and `delete` methods hide the long-running
  operation. The REST client shows the operation.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

import httpx2 as httpx

from managed_agents_demo.config import API_ROOT, Settings

_PERMISSION = re.compile(r"[Pp]ermission '([a-zA-Z0-9_.]+)'")


class ApiError(RuntimeError):
    """The API returned an HTTP error."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message
        match = _PERMISSION.search(message)
        self.permission = match.group(1) if match else None


class OperationError(RuntimeError):
    """A long-running operation finished with an error."""


def default_token_provider() -> Callable[[], str]:
    """Return a function that gives an access token from Application Default Credentials."""
    import google.auth
    import google.auth.transport.requests

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_request = google.auth.transport.requests.Request()

    def token() -> str:
        if not credentials.valid:
            credentials.refresh(auth_request)
        return credentials.token

    return token


class RestClient:
    """A minimal REST client for the Agents API and the operations API."""

    def __init__(
        self,
        settings: Settings,
        token_provider: Callable[[], str] | None = None,
        http: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self._token = token_provider or default_token_provider()
        self._http = http or httpx.Client(timeout=60)

    def url(self, path: str) -> str:
        """Return the full URL for a relative path or a full resource name."""
        if path.startswith("projects/"):
            return f"{API_ROOT}/{path}"
        return f"{self.settings.base_url}/{path}"

    def headers(self) -> dict[str, str]:
        """Return the request headers, with a fresh access token."""
        return {
            "Authorization": f"Bearer {self._token()}",
            "X-Goog-User-Project": self.settings.project,
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        json: Any | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a request and return the JSON body.

        Raises:
            ApiError: If the API returns an HTTP error.
        """
        reply = self._http.request(
            method, self.url(path), json=json, params=params, headers=self.headers()
        )
        if reply.is_error:
            raise ApiError(reply.status_code, _error_message(reply))
        if not reply.content:
            return {}
        return reply.json()


def _error_message(reply: httpx.Response) -> str:
    try:
        body = reply.json()
    except ValueError:
        return reply.text
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return str(body["error"].get("message", body["error"]))
    return reply.text


def operation_name_of(body: dict[str, Any]) -> str:
    """Return the operation name from a long-running operation response."""
    name = body.get("name")
    if not name:
        raise ValueError(f"The response has no operation name: {body}")
    return name


def wait_for_operation(
    rest: RestClient,
    name: str,
    interval: float = 5,
    timeout: float = 600,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    on_tick: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Poll an operation until it is done.

    Args:
        rest: The REST client.
        name: The full operation name.
        interval: Seconds between two polls.
        timeout: Maximum seconds to wait.
        clock: Returns the current time in seconds.
        sleep: Waits for a number of seconds.
        on_tick: Receives the elapsed seconds before each poll.

    Returns:
        The final operation.

    Raises:
        OperationError: If the operation finished with an error.
        TimeoutError: If the operation is not done before the timeout.
    """
    start = clock()
    while True:
        elapsed = clock() - start
        if elapsed > timeout:
            raise TimeoutError(f"The operation is not done after {timeout:.0f} s: {name}")
        if on_tick:
            on_tick(elapsed)
        operation = rest.request("GET", name)
        if operation.get("done"):
            if "error" in operation:
                message = operation["error"].get("message", operation["error"])
                raise OperationError(f"The operation failed: {message}")
            return operation
        sleep(interval)


def make_genai_client(settings: Settings):
    """Return a `google-genai` client for Vertex AI in the `global` location."""
    from google import genai

    return genai.Client(vertexai=True, project=settings.project, location=settings.location)
