# Product Guidelines: Agent Services Starter Pack

## Writing

- Write all text in Simplified Technical English (ASD-STE100). This includes READMEs, code
  comments, docstrings, log lines, and commit messages.
- Short sentences: 20 words or fewer for instructions, 25 for descriptions.
- Active voice. No contractions. No semicolons. One instruction in each sentence.
- Use the same word for the same thing every time. For example: "agent", "Agent Runtime instance",
  "session", "memory", "trace", "observability bucket".
- Mark each claim that is not tested as "Not tested" or "Inference". Mark a tested claim with the
  test that proves it.

## Voice and tone

- Plain and factual. No marketing words.
- Explain the "why" in one sentence before a step.
- State each data residency limit where the reader uses the service, not only in one section.

## Sample code

- Each sample shows one service. A reader must understand it without the other samples.
- Each sample prints what it does, step by step, so that the output reads as a demo.
- Read settings from environment variables or from a gitignored `.env` file. Give a
  `.env.example` with placeholders.
- Comment each line that a reader must change for their own agent.
- When Agent Runtime does a step automatically (for example, it connects the session service), say
  so in a comment. Then a reader does not look for missing code.

## Data residency

- The default region is `asia-southeast1`.
- The Memory Bank sample prints a residency warning: no Google embedding model has ML processing in
  Singapore.
- The observability sample states where the traces are stored, and how the reader can check it.

## Scope

- The pack covers Sessions, Memory Bank, and observability only.
- For Agent Registry, Agent Identity, and Agent Gateway, link to `agent_governance_starter_pack`.
  Do not copy its code.

## Public repository rules

- Placeholders only: no real project IDs, project numbers, org IDs, agent IDs, tokens, or secrets.
- No internal links, internal paths, or customer names.
- Scan every change for secrets and for these items before a commit.
- Stage explicit paths. Do not run `git add .`.
- Work on the feature branch for this starter pack. Never force push.
