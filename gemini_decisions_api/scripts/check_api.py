"""Send one real Decisions API request and print the raw response.

Use this script to confirm the endpoint, the request shape, and the response shape.
It reads the backend settings from .env. It never prints the API key.

Run:
    python scripts/check_api.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import httpx
from dotenv import load_dotenv

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
VERTEX_API_BASE = "https://aiplatform.googleapis.com/v1beta1"

SAMPLE_EMAIL = (
    "Hello, my parcel AB123456789XX was due on Monday. The tracking page has shown "
    "'in transit' for five days. Where is it? I need it before Friday."
)

QUESTIONS = {
    "has_tracking_number": {
        "type": "noul",
        "instructions": "The email contains a parcel tracking number.",
        "criteria": {
            "true_description": "A tracking number is present in the email.",
            "false_description": "No tracking number is present in the email.",
        },
    },
    "category": {
        "type": "choice",
        "instructions": "Which enquiry category does this email belong to?",
        "criteria": {
            "tracking": "Where is my parcel. One or more tracking numbers.",
            "redelivery": "Missed delivery. Book a new delivery or a locker.",
            "weight_dispute": "The customer disputes the billed parcel weight.",
            "scam_check": "The customer asks if a message or a link is real.",
            "import_tax": "A question about import tax or customs charges.",
            "damage_claim": "The parcel arrived damaged. The customer wants money.",
        },
    },
    "complexity": {
        "type": "score",
        "instructions": "Rate how complex this email is to answer.",
        "criteria": [
            "Low: one simple fact answers it.",
            "Medium: needs a lookup and a short explanation.",
            "High: needs a policy decision or a human.",
        ],
    },
}


def build_request() -> tuple[str, dict[str, str], dict]:
    """Return the URL, the headers, and the body for the selected backend."""
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"1", "true", "yes"}
    if use_vertex:
        import google.auth
        import google.auth.transport.requests

        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        if not project:
            sys.exit("GOOGLE_CLOUD_PROJECT is not set. Set it in .env.")
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(google.auth.transport.requests.Request())
        model = os.environ.get("DECISIONS_MODEL") or "gemini-decision-exp"
        url = f"{VERTEX_API_BASE}/projects/{project}/locations/{location}/decisions"
        headers = {"Authorization": f"Bearer {credentials.token}"}
        model_name = model  # Vertex AI takes the bare model ID.
    else:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            sys.exit("GEMINI_API_KEY is not set. Copy .env.example to .env and set the key.")
        model = os.environ.get("DECISIONS_MODEL") or "gemini-decision-1"
        url = f"{GEMINI_API_BASE}/decisions"
        headers = {"x-goog-api-key": key}
        model_name = f"models/{model}"

    body = {"model": model_name, "input": SAMPLE_EMAIL, "questions": QUESTIONS}
    return url, headers, body


def main() -> int:
    """Send the request and print the status, the latency, and the response body."""
    load_dotenv()
    url, headers, body = build_request()
    print(f"POST {url}")
    print(f"model: {body['model']}")

    start = time.perf_counter()
    response = httpx.post(url, headers=headers, json=body, timeout=60)
    latency_ms = (time.perf_counter() - start) * 1000

    print(f"status: {response.status_code}")
    print(f"latency: {latency_ms:.0f} ms")
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)
    return 0 if response.is_success else 1


if __name__ == "__main__":
    sys.exit(main())
