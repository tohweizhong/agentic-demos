# Product Definition: Gemini Decisions API Demo

## Summary

This demo shows how to use the Gemini Decisions API (`gemini-decision-1`) for fast,
typed decisions without text generation. The demo sends one shared input and many
questions in one request. The three question types are yes/no (`noul`), choice, and
score. The demo shows the returned probabilities. Then it branches on them in plain
application code. The demo is a short, self-contained teaching example. It runs from
a clean clone after the steps in its own README.

Source: https://blog.google/innovation-and-ai/technology/developers-tools/gemini-decisions-api/

## Audience

Developers and customer engineers who build agents. They want to see the API work
in a few minutes.

## Use cases

### Part 1: the raw API

1. **Model routing.** A `choice` question and a `score` question rate a user request.
   The code selects a model tier (for example Flash-Lite, Flash, or Pro) from the result.
2. **Tool selection.** A `choice` question selects the next tool for an agent from a
   fixed tool list. `noul` questions check if the request is in scope.
3. **Multimodal input.** One image or PDF is the shared input. Many questions about
   that file go in one request.

### Part 2: the Decisions API inside an ADK agent

4. **Router agent.** A custom ADK agent (a `BaseAgent` subclass) sends one `choice`
   question and gives the request to the selected sub-agent. The routing is
   deterministic code, not an LLM transfer.
5. **Model-tier callback.** A `before_model_callback` sends a `score` question about
   request difficulty and sets the model tier for that turn.

## Comparison

For one scenario, the demo sends the same questions in two ways:

- One Decisions API call.
- One `generateContent` call with a JSON response schema.

The demo shows latency, input tokens, output tokens, and estimated cost next to each other.

## Evaluation

The demo has an evaluation command. It accepts a dataset file and reports accuracy.

### Dataset format

A CSV file with two columns:

| Column  | Content                                |
|---------|----------------------------------------|
| `query` | The user request text.                 |
| `label` | The correct answer, as one option key. |

Example:

```csv
query,label
"My invoice shows a double charge",billing
"The mug arrived cracked",replacements
```

### Question definition

A separate file defines one `choice` question: the instructions and the option keys
with their descriptions. Every `label` in the dataset must be one of these option keys.
The command stops with an error if a label is not an option key.

### Results

For each row, the command sends one Decisions API request. It reports:

- Accuracy: the share of rows where the selected option equals the label.
- A confusion matrix of label against selected option.
- Mean confidence for correct rows and for incorrect rows.
- A results CSV file with the query, label, selected option, and probabilities.

### Sample data

The demo includes a small sample dataset (about 20 rows) of synthetic queries.
It contains no customer data.

## Deliverables

- Part 1: a Python command-line script and a Jupyter notebook.
- Part 2: an ADK agent package that `adk web` and `adk run` can start.
- The evaluation command and the sample dataset.
- A README with setup steps, a `.env.example` file, and a `requirements.txt` file.

## Out of scope

- A web user interface other than `adk web`.
- Production deployment.

## Backends

The demo supports two backends. One environment variable selects the backend.

| Backend | Authentication | Decisions model ID | Status |
|---|---|---|---|
| Gemini Developer API (`v1beta`) | API key from Google AI Studio | `gemini-decision-1` | Default. |
| Vertex AI (`v1beta1`, location `global`) | Application Default Credentials | `gemini-decision-exp` | Early access only. The project must be on the allowlist. |

## Known facts about the API (checked with Duckie on 12 Nov 2026 20:47 SGT)

- Endpoint: `client.decisions.create` in the `google-genai` SDK, with `api_version="v1beta"`.
- A maximum of 1,000 questions for each request, and a maximum of 256K input tokens.
- Zero output tokens. Billing is only for input tokens.

## Open items to test in the first track

- Closed on 12 Nov 2026. See the change log in `tech-stack.md`:
  - `client.decisions.create` is in `google-genai` 3.2.0, which conflicts with ADK. The
    demo uses REST.
  - A change to `llm_request.model` in `before_model_callback` changes the called model.
  - The price is US$0.10 for each 1M input tokens (official pricing page).

## Success criteria

- A new user runs the script in less than 5 minutes after a clone.
- Every use case prints the probabilities and the branch that the code selected.
- The comparison prints real measured numbers. It contains no hardcoded numbers.
- The evaluation command runs on the sample dataset and prints accuracy.
