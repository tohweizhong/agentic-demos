# Spec: MVP of the Gemini Decisions API Demo

## Overview

Build the full demo that `product.md` defines. The scenario is a fictional parcel-delivery
company that receives support emails. The Decisions API classifies each email, checks
it, and selects the next step. All emails, images, and labels are synthetic.

## Scenario

Six enquiry categories (the evaluation labels):

| Key              | Meaning                                               |
|------------------|-------------------------------------------------------|
| `tracking`       | Where is my parcel. One or more tracking numbers.     |
| `redelivery`     | Missed delivery. Book a new delivery or a locker.     |
| `weight_dispute` | The customer disputes the billed parcel weight.       |
| `scam_check`     | The customer asks if a message or a link is real.     |
| `import_tax`     | A question about import tax or customs charges.       |
| `damage_claim`   | The parcel arrived damaged. The customer wants money. |

Two next steps: `AUTO_REPLY` or `HUMAN_DRAFT`.

## Functional requirements

### FR1. Fact check (phase 1)

- Find the `google-genai` version that has `client.decisions.create`. Pin it.
- Send one real request with one question of each type. Record the response shape.
- List the available models. Record the Flash-Lite, Flash, and Pro IDs in `tech-stack.md`.
- Test if a change to `llm_request.model` in `before_model_callback` changes the model
  that ADK calls. Record the result.
- Record the price for each 1M input tokens from the official pricing page.
- If a fact is different from `product.md`, update `product.md` before phase 2.

### FR2. Core module and Part 1 commands (phase 2)

- A small wrapper around `client.decisions.create`. It measures latency and returns
  typed answers.
- A fake client for unit tests.
- Command `triage`: for one email, one `choice` question (category), one `score`
  question (complexity: low, medium, high), and `noul` questions (has a tracking number,
  has a link, asks for money, customer is angry). The code maps the answers to a
  model tier and to `AUTO_REPLY` or `HUMAN_DRAFT`.
- Command `tools`: one `choice` question selects one of six tools (one for each
  category), plus `none`. A `noul` question checks if the email is in scope.
- Command `multimodal`: a script makes a synthetic missed-delivery slip image with
  Pillow. One request asks several questions about the image.

### FR3. Evaluation (phase 3)

- Command `eval --dataset <csv> --question <json>`, as `product.md` defines.
- Sample data: 24 synthetic emails, 4 for each category.

### FR4. Comparison (phase 4)

- Command `compare`: the triage questions go through one Decisions API call and one
  `generateContent` call with a JSON schema. Print latency, tokens, and estimated cost.

### FR5. ADK agent (phase 5)

- A router agent (`BaseAgent` subclass). It sends the category question and gives the
  email to one of six sub-agents. Each sub-agent writes a short draft reply.
- A `before_model_callback` that sends the complexity question and sets the model tier.
- If FR1 shows that the callback cannot change the model, the router selects a
  sub-agent that already uses the correct tier. Record this in `tech-stack.md`.

### FR6. Notebook and README (phase 6)

- A notebook with one section for each use case.
- A README with the setup steps, the commands, and the known limits.
- Add the demo to the top-level `README.md` table.

## Non-functional requirements

- Unit tests do not call the network. Coverage is 70 percent or more.
- A new user runs `triage` in less than 5 minutes after a clone.
- The text obeys `product-guidelines.md`.

## Acceptance criteria

- All commands run against the real API and print real numbers.
- `eval` on the sample data prints accuracy, a confusion matrix, and a results CSV.
- `adk web` starts the agent, and the router selects a sub-agent for each category.
- The diff contains no customer names, no internal links, and no keys.

## Out of scope

- Real tools or MCP servers. The six tools return fixed synthetic data.
- Email ingestion, CRM handoff, and deployment.
- Vertex AI.
