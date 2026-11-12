# Product Guidelines: Managed Agents API Demo

## Writing style

- Write all text in Simplified Technical English (ASD-STE100).
  This includes the README, notebook text, code comments, and terminal output.
- Maximum 20 words in an instruction. Maximum 25 words in a description.
- Use the active voice. Do not use contractions.
- Use the same word for the same thing every time:
  - "agent" for the resource that the Agents API creates.
  - "interaction" for one call to the Interactions API.
  - "session" for a multi-turn conversation.
  - "sandbox" for the agent execution environment.
  - "skill" for a SKILL.md folder. "source" for an item in `base_environment.sources`.

## Tone

- Teach, do not sell. Do not use marketing words such as "powerful" or "seamless".
- State measured facts. Write "the operation took 142 s", not "the operation was slow".

## Safety notices

- The README and the notebook start with a Preview notice. The Managed Agents API is Pre-GA.
- All demo data is synthetic. The README says this, and says why.
- The network allowlist is empty by default. A script that opens network access
  prints a warning that names the allowed domains.
- Every script that creates an agent tells the user to run the cleanup script.

## Publication rules

This demo is in a public GitHub repository.

- No internal shortlinks, internal URLs, or internal source paths.
- No customer names, real project IDs, real bucket names, or customer data.
- No credentials in the code. Use Application Default Credentials.
  Get a short-lived token for the MCP server at run time. Never write a token to disk.
- Give only a `.env.example` file with placeholder values.

## Terminal output

- Every script prints three blocks in this order: the request, the response, the result.
- Print the request body as JSON. Mask every `Authorization` header value.
- Print the agent resource name and the operation name in full.
- While the script polls an operation, print the elapsed time.
- Print the agent output text as it is. Do not shorten it.
- Print a list of files that the agent wrote, with the Cloud Storage path of each file.

## Notebook

- One feature in each section, in the order of `product.md`.
- Each section starts with one short paragraph: the goal, the API, and the expected result.
- Every cell runs from top to bottom without manual changes, after the setup cell.
- The last section deletes the agents.

## Errors

- Error messages state the problem and the fix.
  Example: "GOOGLE_CLOUD_PROJECT is not set. Copy .env.example to .env and set the project ID."
- A permission error names the missing IAM role. Example: `roles/mcp.toolUser`.
- Do not hide API errors. Print the status code and the message.

## Honesty

- Do not hardcode results. All output comes from real API calls.
- If a feature is not built, the README says so.
- If the Preview API rejects a field from the docs, the README records the field and the error.
