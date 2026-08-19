# Deep Dive: Discovery Engine `StreamAssist` Query Lifecycle & Connector Architecture

> **Source References:**
> - [`life_of_a_streamassist_query.md`](http://google3/cloud/ml/agentspace/g3doc/assistant/development/life_of_a_streamassist_query.md) (`go/spark-assistant-life-of-a-streamassist-query`)
> - [`dolphin_life_of_query.md`](http://google3/cloud/ml/agentspace/g3doc/assistant/dolphin_life_of_query.md) (`go/dolphin-life-of-query`)
> - [`bap-integration.md`](http://google3/cloud/ml/agentspace/g3doc/connectors/bap-integration.md) (`go/ge-bap`)
> - [`oauth_recipes.md`](http://google3/cloud/ml/agentspace/g3doc/connectors/oauth_recipes.md)
> - [`toolspec.md`](http://google3/cloud/ml/agentspace/g3doc/connectors/toolspec.md)

---

## 1. Executive Summary & Architecture Overview

Gemini Enterprise (Agentspace / Discovery Engine) handles user queries through the `AssistantService.StreamAssist` RPC—a half-duplex streaming API. 

The architecture is divided into two primary tiers:
1. **Stateful C++ Layer (`AssistantServer`):** Public-facing entry point. Manages session persistence in **Cloud Spanner**, file storage in **GCS**, authentication token brokering via **`DataConnectorService`**, and overall request routing.
2. **Stateless Agentic Reasoning Tier (`DolphinServer` / `Orchestrator`):** Implemented in Python using the **Agent Development Kit (ADK)** or C++ `CorePlannerStrategy`. Handles multi-turn planning, agent-as-a-tool delegation, query rewriting, tool execution via **Model Context Protocol (MCP)** and **Business Application Platform (BAP)**, and final response synthesis.

```mermaid
graph TD
    User([User / Web UI / Prober]) -->|StreamAssist RPC| ESF[Discovery Engine ESF Node<br/>IAM / Chemist / Quota]
    ESF --> SAH[StreamAssistHandler<br/>C++ AssistantServer]
    
    subgraph Stateful C++ Tier
        SAH <--> Spanner[(Spanner Sessions &<br/>OAuth Tokens)]
        SAH <--> GCS[(GCS Uploaded Context Files)]
        SAH --> DCS[DataConnectorService<br/>AcquireAccessToken]
    end

    SAH -->|Select Strategy| Strat{AssistantStrategy}
    
    Strat -->|Default / C++| CP[CorePlannerStrategy<br/>Orchestrator Loop]
    Strat -->|Deep Research| RA[ResearchAssistantStrategy<br/>Grounded Gen Plan]
    Strat -->|No-Code Agents| DA[DirectAgentAssistantStrategy]
    Strat -->|Python Dolphin| DS[DolphinServer / ADK<br/>StreamRunAgent RPC]

    subgraph Dolphin Agent Hierarchy (Python)
        DS --> RootAgent[Root Agent Orchestrator]
        RootAgent --> CA[Connector Agents<br/>Jira, GDrive, SharePoint, Salesforce]
        RootAgent --> FA[Functional Agents<br/>FileAgent, ImagenAgent]
        CA --> QRA[QueryRewriteAgent]
    end

    subgraph Tool & Connector Execution
        CP --> TM[ToolManager]
        CA --> MCP[Local MCP Server Go Proxy]
        MCP --> BAP[BAP Gateway<br/>Business Application Platform]
        BAP --> SaaS[(3P SaaS: Jira, SharePoint, Salesforce)]
        TM --> VSearch[Vertex AI Search / 1P Workspace]
    end

    RootAgent --> LLM[Vertex AI LLM<br/>Gemini 2.5 / 3.5 Flash]
    CP --> LLM
```

---

## 2. The `StreamAssist` Request Lifecycle

### Step 1: ESF & Ingress Routing
* The client opens a half-duplex gRPC/REST stream to `AssistantService:streamAssist`.
* Google Enterprise Services Frontend (ESF) handles IAM authentication, caller validation, Chemist checks, rate limiting, and routes to `StreamAssistHandler`.

### Step 2: Validation & Session Management
* `StreamAssistHandler` validates query length, banned phrases (GOVT checks), and tenant subscription entitlement.
* Loads previous conversational turns from **Cloud Spanner** (`RichSession`) and file metadata from GCS.

### Step 3: Strategy Selection
Based on `AnswerGenerationMode` and request parameters, the handler dispatches execution to an `AssistantStrategy`:
* **`CorePlannerStrategy` (C++):** Native "plan-execute-observe" reasoning loop.
* **`DolphinStrategy` (Python):** Dispatches to `DolphinServer` for multi-agent connector workflows.
* **`ResearchAssistantStrategy`:** Triggers autonomous multi-step Deep Research plan generation.
* **`DirectAgentAssistantStrategy`:** Directly runs a user-configured No-Code agent.

### Step 4: Reasoning & Tool Orchestration Loop
1. **Planning:** The planner generates a `GenerateContentRequest` for Vertex AI including:
   - System instructions (time, timezone, user identity, location, tool rules).
   - Conversation history formatted into User/Model turns.
   - Context files (inlined or RAG search tools).
   - Tool definitions (OpenAPI/MCP function declarations).
2. **Execution:** If the LLM yields `FunctionCall` steps, the orchestrator invokes them concurrently.
3. **Observation:** Tool results (`FunctionResponse`) are appended back into conversation history for the next planner turn.
4. **Termination:** Ends when LLM yields a final text answer, hits a terminal error, or exceeds `kMaxPlannerTurns` (10 turns).

### Step 5: Streaming Delivery & Post-Processing
* Real-time `PlannerStep` events stream to the client:
  - `plan_step` $\rightarrow$ Partial text chunk.
  - `tool_status_update_step` $\rightarrow$ Status messages (e.g. `"Searching Google Drive..."`).
  - `tool_partial_response_step` $\rightarrow$ Intermediate tool results.
* Grounding post-processor attaches `groundingMetadata` and citation chunks.
* Final turn is persisted to Spanner and stream is closed.

---

## 3. Connectors & Authentication Architecture

### A. Connector Types & Deployment (BAP Integration)
Gemini Enterprise integrates with the **Business Application Platform (BAP)** using two deployment models:
* **Managed Connectors (MT):** Multi-tenant shared deployment used in **Gemini Enterprise Biz Edition**.
* **Standard Connectors (MST):** Dedicated multi-single tenant deployment used in **Gemini Enterprise Enterprise Edition**.

Connector definitions are declaratively specified via textprotos in `google3/cloud/connectors/runtime/releases/connector_versions/`.

---

### B. OAuth 2.0 Brokering & Token Flow
For 1P (Google Workspace) and 3P (Microsoft SharePoint, Jira, Salesforce) connectors:

```
[1. User Consent] ──> [2. Auth Code Exchange] ──> [3. Refresh Token Stored in Spanner]
                                                                │
                                                                ▼ (At Query Time)
[6. Remote 3P API] <── [5. BAP Gateway] <── [4. AcquireAccessToken (ya29...)]
```

1. **Setup Phase:** User connects an app $\rightarrow$ OAuth 2.0 consent flow $\rightarrow$ `DataConnectorService` exchanges authorization code for a long-lived **refresh token**, encrypted and stored in Spanner.
2. **Query Phase:** When `StreamAssist` runs, `AssistantServer` calls `DataConnectorService.AcquireAccessToken()` to mint short-lived access tokens without interactive user prompting.
3. **PKCE Support:** Supported connectors use Proof Key for Code Exchange (`authorization_type: OAUTH_PKCE`, `code_challenge_method=S256`).
4. **Auth Expiration (`AUTH_REQUIRED`):** If a 3P token expires or consent is revoked, the tool emits an `auth_required` status with a re-consent URL.

---

### C. Model Context Protocol (MCP) & Toolspec Engine
* **Unified GE MCP Server:** Hosts tools from CDATA connectors, Remote MCP servers, OpenAPI specs, and BYO-MCP servers.
* **Local MCP Proxy:** A lightweight Go plugin runs inside `DolphinServer` as a local MCP server, proxying `tools/call` RPCs directly to the BAP Gateway with the user's OAuth credentials.
* **Toolspec Overrides & Drift Detection:** Tool specifications are snapshot and periodically compared against `google3/cloud/ml/discoveryengine/dolphin/agent_configs/tool_specs/` to detect signature drift across connector releases.

---

## 4. Key Takeaways for Prober Development (`ge-prober`)

| Architectural Invariant | Impact on `ge-prober` Synthetic Testing |
| :--- | :--- |
| **Token Resolution Hierarchy** | Prober must pass an active End-User Credential (EUC `ya29...`) token to allow `DataConnectorService` to resolve Spanner 3P credentials for SharePoint/Jira. |
| **Citation Separation** | Citation metadata is generated by a post-processor and delivered in stream chunks / `groundingMetadata`. The LLM Judge must evaluate semantic text quality without expecting hardcoded inline URLs. |
| **Agentic Deep Research** | Deep Research initial turns generate multi-step research plans (`ResearchAssistantStrategy`). Probers must validate the plan structure rather than expecting shallow answers. |
| **Quick Search Optimization** | Simple search queries bypass multi-step reasoning (`quick_search=True`). Latency targets should reflect fast-path execution. |
| **Mutating Action HITL** | Mutating tools require confirmation; prober must monitor `action_invocation` events for write actions. |
