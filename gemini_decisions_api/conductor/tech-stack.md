# Tech Stack: Gemini Decisions API Demo

## Language

- Python 3.11 or later.

## Libraries

| Library         | Purpose                                                                  |
|-----------------|--------------------------------------------------------------------------|
| `google-genai`  | Decisions API calls and `generateContent` calls. Version 3.2 or later (from Duckie). |
| `google-adk`    | Part 2: the router agent and the model-tier callback.                    |
| `python-dotenv` | Reads `GEMINI_API_KEY` from the `.env` file.                             |
| `rich`          | Tables and colour in the terminal output.                                |
| `jupyter`       | The step-by-step notebook.                                               |
| `pytest`        | Unit tests.                                                              |

The evaluation command uses the standard library `csv` module. It does not use pandas.

## API

- Gemini Developer API, `v1beta` endpoint, with an API key from Google AI Studio.
- Model for decisions: `gemini-decision-1`.
- Models for comparison and ADK sub-agents: Gemini Flash-Lite, Flash, and Pro.
  Track 1 sets the exact model IDs.

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
