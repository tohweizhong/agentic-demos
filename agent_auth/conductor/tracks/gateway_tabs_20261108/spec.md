# Specification: Gateway Tabs (Ingress & Egress)

## Goal
Add two live tabs to the demo client so that the presenter can show the full GEAP security story in one browser window:
1. **Ingress gateway** (`CLIENT_TO_AGENT` with Model Armor inspection and redaction).
2. **Egress gateway** (`AGENT_TO_ANYWHERE` with IAP access policy on MCP tool calls).

## Functional Requirements
- **G1: Ingress gateway tab (`#tab-ingress`, `#ingress-panel`)**
  - Connects to the configured `INGRESS_AGENT_ID` on Agent Runtime (via `/gateway/chat` or `agent_id` parameter).
  - Three sample prompt buttons:
    1. `"what are the names of our west customers?"` (Allowed)
    2. `"what are ssn's for bob johnson and alice brown?"` (Blocked by Model Armor SDP filter on the response)
    3. `"what are bob johnson's and alice brown's email addresses?"` (Allowed)
  - Right-hand decision panel shows an inline SVG diagram of the Ingress flow (`Client -> Ingress Gateway + Model Armor -> Agent`) and a live Cloud Logging decision table (`GET /demo/gateway-logs?kind=ingress`) reading `logName:"modelarmor.googleapis.com%2Fsanitize_operations"`.
- **G2: Egress gateway tab (`#tab-egress`, `#egress-panel`)**
  - Connects to the configured `EGRESS_AGENT_ID` on Agent Runtime.
  - Three sample prompt buttons:
    1. `"I am reviewing the Sterling family's current application. Can you summarize their 2024 and 2025 tax returns and verify if their total household income meets our 2026 debt-to-income requirements?"` (Allowed read tools)
    2. `"Can you send a summary of this to my email jane@example.com?"` (Blocked write tool `send_email`)
    3. `"Can you read my latest emails from the corporate inbox?"` (Allowed read tool)
  - Right-hand decision panel shows an inline SVG diagram of the Egress flow (`Agent -> Egress Gateway + IAP Policy -> MCP Server`) and a live Cloud Logging decision table (`GET /demo/gateway-logs?kind=egress`) reading `logName:"cloudaudit.googleapis.com%2Fdata_access"` (`GatekeeperAuthorizer.AuthorizeUser`, `iap.webServiceVersions.egressViaIAP`).
- **G5: Refresh and Auto-Poll**
  - Each decision panel has a "Refresh logs" button and auto-polls every 15 seconds for up to 3 minutes after a prompt is sent, showing `"Waiting for the log..."` until the new log entry arrives.
  - Rows use `.state-allowed` (`Allowed`, green) and `.state-blocked` (`Blocked`, red) badges with text labels and local + UTC timestamps.
- **G8: Friendly Blocked Banner**
  - When an agent response or error contains `"MCP session connection lost"` or a Model Armor block message, show a clear explanation banner above the message explaining that the gateway blocked the request or tool call.

## Non-Functional Requirements
- **N1: Least Privilege (`agentAuthDemoLogReader`)**
  - Create a custom role with `logging.logEntries.list` (or `roles/logging.viewer` / narrow custom role) granted to the runtime service account only.
  - Behind IAP only (`403` if no IAP email header).
- **N2: Public Repo Hygiene**
  - `INGRESS_AGENT_ID` and `EGRESS_AGENT_ID` come from environment variables (`GET /demo/config`), never hardcoded in tracked files.
