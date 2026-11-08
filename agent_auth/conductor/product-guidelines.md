# Product Guidelines: Agent Auth Demos

## Writing

- Write all text in Simplified Technical English (ASD-STE100): READMEs, UI text,
  code comments, log lines, and commit messages.
- Short sentences: 20 words or fewer for instructions, 25 for descriptions.
- Active voice. No contractions. No semicolons. One instruction in each sentence.
- Use the same word for the same thing every time (for example "auth provider",
  "consent", "agent").
- Mark each claim that is not tested as "Not tested" or "Inference".

## Voice and tone

- Plain and factual. No marketing words.
- Explain the "why" in one sentence before a step.

## UI and UX

- Every wait shows a loading state with text. Never show an empty element.
- Show the current step in words, not with color only.
- Every demo-only feature carries a visible "Demo only" label.
- Accessibility: ARIA roles and labels, keyboard use, and respect for
  "reduce motion".
- Times: local time with the zone, and UTC in brackets. Raw API data stays in UTC.
- Errors: show the error text and remove all spinners.

## Security in the demo

- No public access to any service. Use IAP or an equivalent login.
- Take identity only from a verified source (for example the IAP header).
- Sanitize all model output before it is shown.
- No shell or subprocess in a web request.
- Least privilege: grant on the resource, not on the project, when possible.

## Public repository rules

- Placeholders only: no real project IDs, numbers, org IDs, client IDs, agent IDs,
  tokens, or secrets. Real values go only in a gitignored `.env`.
- No internal links, internal paths, or customer names.
- Scan every change for secrets before a commit.
- Never commit to `main`. Never force push.
