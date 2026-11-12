# Tech Stack: Gemini Decisions API Demo

## Language

- Python 3.11 or later.

## Libraries

| Library         | Purpose                                                                  |
|-----------------|--------------------------------------------------------------------------|
| `google-genai`  | `generateContent` calls for the comparison. Version 2.x, because ADK requires it. |
| `httpx`         | The Decisions API REST client. ADK already installs it.                  |
| `google-auth`   | Access tokens for the Vertex AI backend (ADC). ADK already installs it.  |
| `google-adk`    | Part 2: the router agent and the model-tier callback.                    |
| `python-dotenv` | Reads `GEMINI_API_KEY` from the `.env` file.                             |
| `rich`          | Tables and colour in the terminal output.                                |
| `jupyter`       | The step-by-step notebook.                                               |
| `pytest`        | Unit tests.                                                              |

The evaluation command uses the standard library `csv` module. It does not use pandas.

## API

- Default backend: Gemini Developer API, `v1beta` endpoint, with an API key from
  Google AI Studio. Model for decisions: `gemini-decision-1`.
- Second backend: Vertex AI, `v1beta1` endpoint, location `global`, with Application
  Default Credentials. Model for decisions: `gemini-decision-exp`. It is in early
  access, and the project must be on the allowlist.
- The `google-genai` SDK selects the backend from the environment:
  `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.
  The demo code does not change between backends. Only the model ID changes.
- Tier models (from the Gemini Developer API model list on 12 Nov 2026):
  `gemini-3.5-flash-lite` (lite), `gemini-3.8-flash` (flash), and `gemini-4-argon` (pro).
  Environment variables can override them.

## Environment

- A local virtual environment in the demo folder (`.venv/`).
  It is not shared with other demos.
- `requirements.txt` with pinned versions.

## Tests

- Unit tests use a fake Decisions API client. They do not call the network.
- One integration test calls the real API. It runs only when `GEMINI_API_KEY` is set.

## Not used

- No backend framework, no frontend framework, and no database.
  The demo is a command-line script, a notebook, and an ADK agent.

## Change log

### 12 Nov 2026: Decisions API through REST, not the SDK

- `google-genai` 3.2.0 is the first version with Decisions code (`client.decisions.create`).
  Versions 2.34.0 and 3.0.0 do not have it.
- `google-adk` 2.14.0, the newest version, requires `google-genai>=2.30,<3`.
  Thus the two packages cannot install together.
- The 3.2.0 Decisions code sends `POST /{api_version}/decisions`. It shows no Vertex AI
  project path.
- Decision: the demo calls the Decisions endpoint with a small `httpx` client. The request
  shape is copied from the 3.2.0 SDK types. Part 1 and Part 2 use the same client.
- Change back to `client.decisions.create` when ADK accepts `google-genai` 3.x.

### 12 Nov 2026: First real call on the Gemini Developer API (confirmed)

- Request: `POST https://generativelanguage.googleapis.com/v1beta/decisions`, header
  `x-goog-api-key`, body `{"model": "models/gemini-decision-1", "input": "<text>",
  "questions": {<key>: <question>}}`. Status 200.
- `noul` answer: `{"type", "noul", "confidence"}`. `confidence` equals `noul` here.
- `choice` answer: `{"type", "choice", "confidence", "probabilities"}`. `probabilities` has
  all option keys. `confidence` equals the probability of the selected option.
- `score` answer: `{"type", "score", "confidence", "probabilities", "legend"}`. The keys of
  `probabilities` and `legend` are level indexes as strings ("0", "1", ...). `score` is
  the expected value. There is no `most_likely_level` field.
- `usage`: `total_tokens`, `total_input_tokens`, `total_output_tokens` (0), and
  `input_tokens_by_modality`.
- Measured: 391 input tokens, 0 output tokens, 734 ms for 3 questions on a 40-word email.
  This was one call from a Cloudtop in Singapore. It is not a benchmark.

### 12 Nov 2026: Facts from the official documentation

Sources: https://ai.google.dev/gemini-api/docs/pricing and
https://ai.google.dev/gemini-api/docs/decisions-api (read on 12 Nov 2026).

- Price of `gemini-decision-1`: US$0.10 for each 1M input tokens (paid tier). Output: not
  applicable. The free tier is free of charge. The Batch API is not supported.
- Shared input tokens are billed one time for each request. Each question adds tokens
  for its instructions and criteria.
- Limits: 1 to 1,000 questions. 2 to 255 options for each `choice` question. 2 to 255
  non-empty levels for each `score` question. Question keys: 1 to 64 characters,
  `[A-Za-z0-9_-]+`. Option keys: 1 to 128 characters.
- Image input block: `{"type": "image", "data": <base64>, "mime_type": "image/png"}`.
- The documentation does not show `include_none_of_above`. The demo adds a `none` option
  as a normal option.
- Tier prices for the comparison (paid tier, input and output for each 1M tokens):
  `gemini-3.5-flash-lite` US$0.30 and US$2.50. `gemini-3.8-flash` US$0.75 and US$3.75
  until 31 Dec 2026. `gemini-4-argon` US$2.00 input until 30 Nov 2026.

### 12 Nov 2026: ADK model change in before_model_callback (confirmed)

- In ADK 2.14.0, `Gemini.generate_content_async` sends `llm_request.model` to the API
  (`google/adk/models/google_llm.py`). The flow sets `llm_request.model` from the agent
  before the callback runs.
- `tests/test_adk_model_switch.py` confirms it: without a callback, ADK calls the agent
  model. When the callback sets `llm_request.model`, ADK calls the new model.

### 12 Nov 2026: First Vertex AI request (before early access)

- Request: `POST https://aiplatform.googleapis.com/v1beta1/projects/<project>/locations/global/decisions`
  with an ADC token. Result: `404 Method not found`, detail "Method CreateDecisionHttp not
  found ... not visible to labels: {PUBLIC}". The URL maps to the Decisions method. The
  project does not have the `DECISIONS_API_EAP` visibility label yet.
- Duckie says that Vertex AI needs the bare model ID (`"model": "gemini-decision-exp"`), not
  `publishers/google/models/...`. The client now sends the bare ID. This is not confirmed by
  a real call. Duckie also said that the Gemini Developer API uses `gemini-decision-eap`, but
  the real call with `models/gemini-decision-1` worked, so treat Duckie's model facts with care.
- Expected errors in order: no visibility label gives `404 Method not found`. No allowlist tag
  gives `404 Publisher model ... was not found`. No quota gives `429`.

### 12 Nov 2026: Judge method and first result

- Cohen's kappa uses the standard library: (observed - expected) / (1 - expected). Kappa is
  "n/a" when both label lists hold only one class.
- Review flag: for a `score` check, the confidence is the probability of the pass or fail
  decision (the sum over the passing levels), not the probability of the top level. In the
  first run, the top-level confidence for `tone` had a median of 0.61, because the model
  split between "Neutral" and "Polite". That marked 16 of 20 rows for review. With the
  pass-decision probability, 3 of 20 rows need review.
- Result on 20 synthetic answers: 20 of 20 correct, kappa 1.00, 8,020 input tokens.

