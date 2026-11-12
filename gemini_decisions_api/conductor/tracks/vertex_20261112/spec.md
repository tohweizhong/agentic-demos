# Spec: Test the Vertex AI backend

## Overview

The demo supports Vertex AI, but nobody has tested it. The Decisions API on Vertex AI is in
early access. This track starts when the test project gets the three early-access grants:
the model allowlist tag, the visibility label, and a quota override.

## Functional requirements

- Run `scripts/check_api.py` with `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`,
  and `GOOGLE_CLOUD_LOCATION=global`. Record the status, the response shape, and the latency.
- If the Vertex AI request shape or model name differs from the code, fix `client.py` and
  its unit tests.
- Run `triage`, `eval`, and the ADK integration test on Vertex AI.
- Change the README backend table from "Not tested" to the result.

## Acceptance criteria

- `check_api.py` returns status 200 on Vertex AI.
- The README states the tested date and the result.

## Out of scope

- Requests for early access. A person makes them outside this repository.
