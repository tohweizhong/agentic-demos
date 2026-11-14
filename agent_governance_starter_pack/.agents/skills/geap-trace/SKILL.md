---
name: geap-trace
description: Read the Cloud Trace spans of one agent session and report the governance decisions - tool calls, Model Armor checks at the gateway, MCP server calls, and tool calls that the gateway probably denied. Use when the user asks what happened in a session, why a tool call failed, or for trace evidence of a denial.
---

# Skill: geap-trace

This skill runs `scripts/read_session_trace.sh`. The script is read-only. It reads the Cloud Trace
API v1 in the project from `terraform output project_id`.

## Steps

1. Get the session ID or the trace ID.
   - `scripts/ask_agent.sh` prints the session ID when it creates a session.
   - In the Cloud console, the agent "Traces" page shows the session ID and the trace IDs.
   - If the user has neither ID, ask for it. Do not guess an ID.
2. Run one of these commands:

   | The user has | Command |
   |---|---|
   | A session ID | `scripts/read_session_trace.sh SESSION_ID --since 1d` |
   | A session that is older than 1 day | `scripts/read_session_trace.sh SESSION_ID --since 30d` |
   | One trace ID | `scripts/read_session_trace.sh --trace TRACE_ID` |
   | A request for machine-readable output | Add `--json` |

3. If the script prints `TRACE: NOT_APPLICABLE` (exit 3), stop. Tell the user that the agent does not
   send spans to Cloud Trace, so no trace evidence exists. For the starter pack agent, the span export
   fails today (backlog item 36). Use `scripts/read_audit_log.sh` for the gateway evidence. If the script prints
   `TRACE: NOT_FOUND`, check the session ID with the user, or wait 1 to 2 minutes and run it again.
4. Read the rows and the summary line. Use this table:

   | Row | Result | Meaning |
   |---|---|---|
   | `TOOL` | `OK` | The tool returned a result |
   | `TOOL` | `NO_DOWNSTREAM` | The tool call failed, and no gateway or MCP span is below it. The egress gateway probably denied the call (for example an IAP policy denial). ADK reports this as "MCP tool execution failed: Server returned an error response" or "MCP session connection lost" |
   | `TOOL` | `ERROR` | The tool call reached the gateway or the MCP server, and then failed |
   | `MODEL_ARMOR` | `ALLOW 200` | Model Armor found no problem in the prompt or the response |
   | `MODEL_ARMOR` | `MODIFY` or `BLOCK` | Model Armor changed or blocked the content. The detail column names the template and the finding |
   | `MCP_HTTP` | Not `2xx` | The MCP server on Cloud Run returned an error |

5. For each `NO_DOWNSTREAM` row, confirm the denial. Run `scripts/read_audit_log.sh 1h`, or a
   longer window that covers the row time. Look for a gateway row with status `403`.
   - IAP policy V1 writes the `403 DENIED` row to the gateway request log.
   - IAP policy V2 does not write this row (b/583376130). If there is no row, say that the denial
     is probable but not confirmed in the logs.
6. Report to the user:
   - The number of traces and tool calls.
   - Each `NO_DOWNSTREAM`, `ERROR`, `MODIFY`, or `BLOCK` row, with its time in SGT and the tool name.
   - Which result you confirmed in the logs, and which result is only trace evidence.

## Rules

- Do not paste the full `tool_call_args` or `tool_response` values in a report. They can hold
  personal data. The script shortens them. Keep them short.
- If the script returns `429 RESOURCE_EXHAUSTED` or `403` from the Cloud Trace API, stop. Tell the
  user to check that the caller has `roles/cloudtrace.user` on the project. Do not retry in a loop.
- Use `--project` only when the user names a project. The default is the Terraform project.
