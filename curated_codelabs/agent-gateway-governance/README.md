# Agent Gateway governance demo (IAP + Model Armor)

A ready-to-reuse demo of **Agent Gateway** on Google Cloud. An ADK agent on Agent Runtime calls
three MCP servers on Cloud Run. Every outbound call goes through Agent Gateway, which checks
identity with IAP and content with Model Armor.

This folder does not hold the demo code. It holds the notes that you need to run the public
codelab again, fast, and to present it.

| Item | Link |
|---|---|
| Codelab | [Governing agentic workloads with Agent Gateway](https://codelabs.developers.google.com/cloudnet-agent-gateway) |
| Sample code | [GoogleCloudPlatform/cloud-networking-solutions, `demos/agent-gateway`](https://github.com/GoogleCloudPlatform/cloud-networking-solutions/tree/main/demos/agent-gateway) |
| Last full run | October 2026, region `us-central1` |

## What the demo shows

| Control | What the audience sees |
|---|---|
| Agent identity | The agent has its own identity. IAM grants go to the agent, not to a service account. |
| Agent Registry | The agent finds its MCP servers at runtime from the registry. The gateway blocks hosts that are not in the registry. |
| IAP egress policy (`REQUEST_AUTHZ`) | `roles/iap.egressor` on each MCP server. A CEL condition allows read-only tools and blocks write tools. |
| Model Armor (`CONTENT_AUTHZ`) | Prompt injection checks and redaction of sensitive data, such as SSNs, in tool responses. |
| Observability | Gateway request logs show the tool name and the allow or deny result for each call. |

## Architecture

```mermaid
flowchart LR
    user["User"]
    ge["Gemini Enterprise app"]
    pg["Agent Runtime Playground"]
    agent["Mortgage agent on Agent Runtime (agent identity)"]
    reg["Agent Registry (MCP servers and endpoints)"]

    subgraph agw ["Agent Gateway (egress)"]
        iap["IAP authz extension (REQUEST_AUTHZ)"]
        ma["Model Armor authz extension (CONTENT_AUTHZ)"]
    end

    subgraph run ["MCP servers on Cloud Run"]
        dms["legacy-dms"]
        inc["income-verification"]
        mail["corporate-email"]
    end

    user --> ge
    user --> pg
    ge --> agent
    pg --> agent
    agent -- "list MCP servers" --> reg
    agent -- "every tool call" --> agw
    iap -- "allowed calls" --> run
    ma -. "scan and redact" .-> run
```

## Flow of one tool call

The follow-up prompt asks the agent to email a summary. `send_email` is a write tool, so IAP
blocks it.

```mermaid
sequenceDiagram
    participant U as User
    participant A as Mortgage agent
    participant G as Agent Gateway
    participant I as IAP
    participant M as corporate-email MCP

    U->>A: "Send a summary to my email"
    A->>G: tools/call send_email
    G->>I: Check roles/iap.egressor and CEL condition
    I-->>G: DENIED, tool is not read-only
    G-->>A: HTTP 403
    A-->>U: "I could not send the email"
    U->>A: "Read my latest emails"
    A->>G: tools/call read_email
    G->>I: Check roles/iap.egressor and CEL condition
    I-->>G: ALLOWED, tool is read-only
    G->>M: Forward the call
    M-->>A: Emails, with addresses redacted
```

## Files in this folder

| File | Use it for |
|---|---|
| [RUNBOOK.md](RUNBOOK.md) | Deploy the demo from zero. Includes the fixes for the problems that the codelab does not mention. |
| [TALKING_POINTS.md](TALKING_POINTS.md) | Present the demo: script, prompts, expected results, and audience questions. |

## Time and cost

| Item | Value |
|---|---|
| Deploy time | About 90 minutes, with the fixes in the runbook |
| Always-on settings | 3 Cloud Run services with 1 minimum instance each (1 vCPU, 512 MiB), and the agent with 2 minimum instances (4 vCPU, 8 GiB) |
| Measured idle cost | About USD 1.10 a day, from the Billing report after 4 days in October 2026 |
| Clean up | Delete the agent first, then run `terraform destroy`. See the runbook. |

What the measured cost contained:

| Resource | Cost per day | Note |
|---|---|---|
| Cloud Run minimum instances | About USD 0.95 | Idle rate for CPU and memory. This was almost all of the cost. |
| Cloud NAT | About USD 0.14 | IP usage and gateway uptime |
| Agent on Agent Runtime, Agent Gateway | USD 0 | No charge appeared while idle. Prices can change, so check the Billing report. |

> [!TIP]
> To see the real cost, open the Billing report, filter on your demo project, and group by SKU.
> Do not set the Cloud Run minimum instances to 0 before a demo. A cold start takes longer than the
> 5-second MCP timeout, and the agent then loses its tools for that request.
