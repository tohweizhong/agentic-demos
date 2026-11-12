# Product Guidelines: Gemini Decisions API Demo

## Writing style

- Write all text in Simplified Technical English (ASD-STE100).
  This includes the README, notebook text, code comments, and terminal output.
- Maximum 20 words in an instruction. Maximum 25 words in a description.
- Use the active voice. Do not use contractions.
- Use the same word for the same thing. Use "question", not "probe" or "check".

## Tone

- Teach, do not sell. Do not use marketing words such as "blazing fast".
- State measured facts. Write "the call took 210 ms", not "the call was fast".

## Publication rules

This demo is in a public GitHub repository.

- No internal shortlinks, internal URLs, or internal source paths.
- No customer names, real project IDs, or customer data.
- No API keys in the code. Read the key from the environment.
  Give only a `.env.example` file with placeholder values.

## Terminal output

- Every use case prints three blocks in this order: the input, the answers, the decision.
- Print probabilities with two decimal places.
- Print a table for answers with many options.
- Print latency in milliseconds and token counts as integers.
- Mark a value as "estimated" if the code computes it from a price constant.

## Notebook

- One use case in each section.
- Each section starts with one short paragraph: the goal, the question type, and the
  expected result.
- Every cell runs from top to bottom without manual changes.

## Errors

- Error messages state the problem and the fix.
  Example: "GEMINI_API_KEY is not set. Copy .env.example to .env and set the key."
- Do not hide API errors. Print the status code and the message.

## Honesty

- Do not hardcode results. All numbers come from real API calls.
- If a feature is not built, the README says so.
