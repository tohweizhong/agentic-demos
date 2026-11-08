# Product Definition: Agent Auth Demos

## Summary

Self-contained demos that show how an ADK agent on Agent Runtime gets credentials
for other services. The agent uses its own Agent Identity for Google Cloud, and
Auth Manager for third-party credentials, with or without a user. Each sub-demo has
its own agent, deploy scripts, and clean-up. All sub-demos share one demo client
on Cloud Run with IAP.

## Audience

- Customer engineers who present agent identity and governance to customers.
- Customer platform and security teams who evaluate the pattern.

## Goals

1. Show that each agent has its own identity, not a shared service account.
2. Show user-delegated access (3LO): the agent acts only after the user consents.
3. Show least privilege: one agent, one auth provider, narrow roles.
4. Show audit: which agent used which provider, for which user, and when.
5. Reset and repeat the demo in less than 2 minutes.

## Sub-demos

| Sub-demo | Status |
|---|---|
| `3lo_github` | Tested |
| `2lo_client_credentials`, `api_key`, `outbound_bindings`, `token_exchange_obo`, `dynamic_client_registration`, `agent_to_aws`, `mcp_server_oauth`, `negative_tests` | Planned |

## Requirements (current)

### Demo client

- R1 Runs on Cloud Run with IAP. No public access.
- R2 Takes the Auth Manager user ID from the IAP login header only.
- R3 Resumes the chat by itself after the consent, exactly once.
- R4 Shows loading states. Never shows an empty chat bubble.
- R5 Renders answers as sanitized Markdown.
- R6 Has a "New conversation" button. It keeps the stored token.
- R7 Project and location are dropdowns, filled from server settings.
- R8 "How 3LO works" tab: diagram with 12 steps, live highlight, timing table.
- R9 Demo controls panel (demo only): reset Auth Manager consent, show access
  summary, terminal-style output with the matching gcloud command. No shell.
- R10 Times in local time with UTC in brackets. Raw JSON stays in UTC.

### Agent and platform

- R11 Deploy with `adk deploy agent_engine` (Python object, named methods).
- R12 Model called in the `global` location.
- R13 Agent principal gets `roles/agentidentity.user` on its provider only.
- R14 Build with a dedicated build service account.
- R15 Custom roles with one permission each for the demo controls.

### Repository

- R16 Placeholders only. No real IDs, secrets, tokens, or internal links.
- R17 Each sub-demo runs from a clean clone with only its README.
- R18 Each sub-demo has a clean-up script that deletes only its own resources.

## Backlog

- B1 Access summary view: filter to the current user and agent, sort newest first,
  an explanation line, and the agent display name.
- B2 Option: "New conversation" also resets the consent (decision open).
- B3 "Ingress gateway" tab in the demo UI: Completed (`gateway_tabs_20261108`).
- B4 "Egress gateway" tab in the demo UI: Completed (`gateway_tabs_20261108`).
- B5 After B3 and B4: one combined journey view (3LO, ingress, egress, audit).
- B6 "MCP" info tab in the demo UI: explain MCP tool annotations (`readOnlyHint`,
  `destructiveHint`), tool discovery (`tools/list`), and per-tool CEL policies.

## Out of scope

- Production use. The demo controls must not exist in a production client.
- Automatic GitHub token revoke. GitHub needs the user token, which only Auth
  Manager holds.
