# Talking points: Agent Gateway governance demo

Use this file to present the demo in 10 to 15 minutes. Run the deployment first with
[RUNBOOK.md](RUNBOOK.md), and check that the prompts below give the expected results.

## The story in one sentence

"Agents call tools for you. Agent Gateway puts a policy checkpoint in front of every tool call, so
that you control which agent can call which tool, and what data can leave."

## Problem to open with

- Agents act on their own. They choose which tools to call and which data to send.
- Each team builds its own agents and MCP servers. Security teams cannot review each one.
- Network firewalls see hosts and ports. They cannot see "this agent called `send_email`".

## Demo script

| # | Show | Say |
|---|---|---|
| 1 | The architecture diagram in [README.md](README.md) | "The agent never talks to a tool directly. Every call goes through the gateway." |
| 2 | The agent page in the console, Identity tab | "The agent has its own identity. We grant access to the agent itself, not to a shared service account." |
| 3 | Agent Registry: MCP servers and endpoints | "The registry is the catalog of approved tools. The agent finds its tools here. The gateway blocks hosts that are not in the registry." |
| 4 | Playground or Gemini Enterprise: prompt A | "The agent reads documents and checks income. Note that the SSNs are redacted. Model Armor removes them from the tool response." |
| 5 | Prompt B | "Now the agent tries to send email. IAP blocks it, because this agent may only use read-only tools on the email server." |
| 6 | Prompt C | "Read-only email still works. The control is per tool, not per server." |
| 7 | IAP Data Access audit log (query below) | "Each decision is logged: the agent, the tool, the MCP method, and allow or deny. This is your audit trail." |
| 8 | Cloud Trace for one request | "The trace shows the call came from Gemini Enterprise, through the agent, to the tool." |

## Prompts and expected results

| Prompt | Expected result |
|---|---|
| A. "I am reviewing the Sterling family's current application. Can you summarize their 2024 and 2025 tax returns and verify if their total household income meets our 2026 debt-to-income requirements?" | A summary from the document tool and the income tool. SSNs are redacted. |
| B. "Can you send a summary of this to my email jane@example.com?" | The agent says that it could not send the email. The IAP Data Access audit log shows `granted: false` for `tools/call` with `read_only_hint: false`. |
| C. "Can you read my latest emails from the corporate inbox?" | A list of emails. Email addresses show as `[EMAIL_ADDRESS]`. |

The message for prompt B can be a technical error, such as "MCP session connection lost". It still
means that the gateway blocked the call. In the agent log, the MCP call returns `403 Forbidden`, and
ADK then reports the lost session.

Show the denial in the IAP Data Access audit log. In a test in November 2026, the gateway request
log showed only tunnel (`CONNECT`) entries for the denied call. It had no `403` entry, but it had
`ALLOWED` entries for allowed calls. The IAP audit log had the decision:

```bash
gcloud logging read 'logName:"cloudaudit.googleapis.com%2Fdata_access" AND protoPayload.methodName="GatekeeperAuthorizer.AuthorizeUser" AND protoPayload.authorizationInfo.permission="iap.webServiceVersions.egressViaIAP" AND protoPayload.authorizationInfo.granted=false' \
  --project=${PROJECT_ID} --freshness=1h --limit=5 \
  --format="table(timestamp, protoPayload.metadata.mcp_attributes.mcp_method, protoPayload.metadata.mcp_attributes.mcp_annotations.read_only_hint, protoPayload.status.code)"
```

Expected row: `tools/call`, `False`, `7` (permission denied). The filter on `egressViaIAP` hides
denials from other IAP uses in the project, for example a web app behind IAP.

## Key messages

1. **Central control.** One gateway applies policy to all agents. Teams do not build security into
   each agent.
2. **Least privilege for agents.** IAM grants go to one agent identity, for one MCP server, and can
   be limited to read-only tools with a CEL condition.
3. **Data protection in the path.** Model Armor scans prompts and tool responses, and removes
   sensitive data before the agent sees it.
4. **Safe rollout.** Start IAP in dry-run mode, read the decisions in the logs, then enforce.
5. **Works with Gemini Enterprise.** The same agent, with the same controls, appears in the Agent
   Gallery for business users.

## Questions the audience can ask

| Question | Answer |
|---|---|
| Does the agent code change? | No security code in the agent. The agent calls tools as usual. The gateway applies the policy. |
| Can one agent use a tool and another agent not? | Yes. Grants are per agent identity, per MCP server, and optionally per tool. |
| What happens if the policy check fails? | It depends on the fail mode. The demo uses fail-open for a smooth demo. Production must use fail-closed. |
| Can we try it without blocking traffic? | Yes. Dry-run mode logs each decision and blocks nothing. |
| What happens if someone deletes the gateway policies? | The gateway denies all agent traffic. It fails closed, so a missing policy does not open the gateway. This was seen in a real run. |
| Which regions? | The demo uses `us-central1`. Check the current documentation for your region before you promise anything. |
| Does it work for agents outside Agent Runtime? | The demo covers Agent Runtime. Check the current documentation for other runtimes. |

## Do not say

- Do not promise region support or dates. Check the current documentation first.
- Do not say that the extension setting proves enforcement. Show the gateway request log.
- Do not show the fail-open setting as a production setting.

## Before you present: checklist

- [ ] All 3 prompts give the expected results today.
- [ ] The gateway request log query returns the `send_email` deny.
- [ ] You know the cost per hour, and you have a time to delete the demo.
