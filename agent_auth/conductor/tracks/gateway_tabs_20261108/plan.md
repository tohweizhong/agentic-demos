# Implementation Plan: Gateway Tabs (Ingress & Egress)

## Phase 1: Backend Endpoints & Unit Tests
- [ ] Task: Write failing unit tests in `tests/test_backend.py` for `/demo/config` (`ingressAgentId`, `egressAgentId`), `/demo/gateway-logs?kind=ingress`, and `/demo/gateway-logs?kind=egress`.
- [ ] Task: Implement `GET /demo/gateway-logs` in `main.py` using Cloud Logging REST API (`entries:list`) with IAP check and parser for Model Armor (`sanitize_operations`) and IAP Egress (`GatekeeperAuthorizer.AuthorizeUser`).

## Phase 2: Ingress & Egress Tabs UI & Browser Tests
- [ ] Task: Write failing Playwright tests in `tests/test_gateway_tabs.py` for:
  - Ingress tab sample prompt buttons, chat streaming, friendly blocked banner, and Model Armor decision table.
  - Egress tab sample prompt buttons, chat streaming, friendly `"MCP session connection lost"` banner, and IAP decision table.
  - Refresh button and auto-poll indicator.
- [ ] Task: Implement `#tab-ingress`, `#tab-egress`, `#ingress-panel`, `#egress-panel` in `index.html`, `script.js`, and `style.css`.
- [ ] Task: Update `client/README.md` and `deploy/04_deploy_client.sh` (add `INGRESS_AGENT_ID`, `EGRESS_AGENT_ID`, and `agentAuthDemoLogReader` custom role).

## Phase 3: Deploy & Verify
- [ ] Task: Run full pytest suite, coverage check (>=80%), and git hygiene check.
- [ ] Task: Commit, push branch `feat/gateway-tabs`, and deploy to Cloud Run.
