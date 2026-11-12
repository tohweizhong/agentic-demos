"""A small REST client for the Gemini Decisions API.

Why REST and not the SDK: ``google-genai`` 3.2.0 is the first version with
``client.decisions.create``, but ``google-adk`` 2.14.0 requires ``google-genai<3``.
This client sends the same JSON that the SDK sends, so the two packages are not needed
together.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from decisions_demo.config import Backend, Config
from decisions_demo.questions import Question, validate_questions

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
VERTEX_API_BASE = "https://aiplatform.googleapis.com/v1beta1"

DecisionInput = str | dict[str, Any] | list[dict[str, Any]]


class DecisionsAPIError(RuntimeError):
    """The API returned an error, or the response has an unknown shape."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message if status is None else f"HTTP {status}: {message}")
        self.status = status


@dataclass(frozen=True)
class NoulAnswer:
    """Answer to a yes/no question."""

    probability: float
    confidence: float

    @property
    def value(self) -> bool:
        """True when the probability is 0.5 or more."""
        return self.probability >= 0.5


@dataclass(frozen=True)
class ChoiceAnswer:
    """Answer to a choice question."""

    choice: str
    confidence: float
    probabilities: dict[str, float]

    def ranked(self) -> list[tuple[str, float]]:
        """Return the options from the highest probability to the lowest."""
        return sorted(self.probabilities.items(), key=lambda item: item[1], reverse=True)


@dataclass(frozen=True)
class ScoreAnswer:
    """Answer to a score question. Levels are integers from 0 (lowest)."""

    score: float
    confidence: float
    probabilities: dict[int, float]
    legend: dict[int, str]

    @property
    def most_likely_level(self) -> int:
        """The level with the highest probability. The API does not return this field."""
        return max(self.probabilities, key=self.probabilities.__getitem__)


Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer


@dataclass(frozen=True)
class DecisionResult:
    """All answers for one request, with usage and latency."""

    answers: dict[str, Answer]
    input_tokens: int
    output_tokens: int
    latency_ms: float


def _parse_answer(key: str, data: Mapping[str, Any]) -> Answer:
    kind = data.get("type")
    if kind == "noul":
        return NoulAnswer(probability=float(data["noul"]), confidence=float(data["confidence"]))
    if kind == "choice":
        return ChoiceAnswer(
            choice=data["choice"],
            confidence=float(data["confidence"]),
            probabilities={k: float(v) for k, v in data["probabilities"].items()},
        )
    if kind == "score":
        return ScoreAnswer(
            score=float(data["score"]),
            confidence=float(data["confidence"]),
            probabilities={int(k): float(v) for k, v in data["probabilities"].items()},
            legend={int(k): v for k, v in data.get("legend", {}).items()},
        )
    raise DecisionsAPIError(f"Unknown answer type {kind!r} for question {key!r}.")


def parse_response(body: Mapping[str, Any], latency_ms: float) -> DecisionResult:
    """Convert the JSON body of a Decisions API response to a DecisionResult."""
    answers = {key: _parse_answer(key, value) for key, value in body.get("answers", {}).items()}
    usage = body.get("usage", {})
    return DecisionResult(
        answers=answers,
        input_tokens=int(usage.get("total_input_tokens", 0)),
        output_tokens=int(usage.get("total_output_tokens", 0)),
        latency_ms=latency_ms,
    )


def image_block(data: bytes, mime_type: str) -> dict[str, str]:
    """Return an inline image input block."""
    return {"type": "image", "data": base64.b64encode(data).decode("ascii"), "mime_type": mime_type}


def _default_token_provider() -> str:
    """Return an access token from Application Default Credentials."""
    import google.auth
    import google.auth.transport.requests

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


class DecisionsClient:
    """Sends Decisions API requests to the backend that the Config selects."""

    def __init__(
        self,
        config: Config,
        http_client: httpx.Client | None = None,
        token_provider: Callable[[], str] | None = None,
    ) -> None:
        self.config = config
        self._http = http_client or httpx.Client(timeout=60)
        self._token_provider = token_provider or _default_token_provider

    def _endpoint(self) -> tuple[str, dict[str, str], str]:
        """Return the URL, the auth headers, and the model resource name."""
        model = self.config.decisions_model
        if self.config.backend is Backend.VERTEX_AI:
            url = (
                f"{VERTEX_API_BASE}/projects/{self.config.project}"
                f"/locations/{self.config.location}/decisions"
            )
            headers = {"Authorization": f"Bearer {self._token_provider()}"}
            # Vertex AI takes the bare model ID (from Duckie, 12 Nov 2026). Confirm it with a
            # real call after the project gets early access.
            return url, headers, model
        headers = {"x-goog-api-key": self.config.api_key or ""}
        return f"{GEMINI_API_BASE}/decisions", headers, f"models/{model}"

    def decide(self, input: DecisionInput, questions: Mapping[str, Question]) -> DecisionResult:
        """Ask all questions about one shared input in one request."""
        validate_questions(questions)
        url, headers, model = self._endpoint()
        body = {"model": model, "input": input, "questions": dict(questions)}

        start = time.perf_counter()
        response = self._http.post(url, headers=headers, json=body)
        latency_ms = (time.perf_counter() - start) * 1000

        if not response.is_success:
            try:
                message = response.json().get("error", {}).get("message", response.text)
            except ValueError:
                message = response.text
            raise DecisionsAPIError(message, status=response.status_code)
        return parse_response(response.json(), latency_ms=latency_ms)
