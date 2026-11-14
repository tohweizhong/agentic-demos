#!/usr/bin/env bash
# Exports the Cloud Trace spans of one agent session as a table of governance
# decisions: model calls, tool calls, Model Armor checks at the gateway, and the
# MCP server calls behind the gateway. Times are in Singapore time (SGT).
#
# Usage:
#   scripts/read_session_trace.sh SESSION_ID [--since 7d] [--project PROJECT_ID] [--json]
#   scripts/read_session_trace.sh --trace TRACE_ID [--project PROJECT_ID] [--json]
#
# - SESSION_ID is the Agent Runtime session ID. The script finds the traces with
#   the span label gen_ai.conversation.id = SESSION_ID.
# - --since is how far back to search: Nm, Nh, or Nd (default 7d). Cloud Trace
#   keeps spans for 30 days.
# - --project defaults to the Terraform output project_id.
# - --json prints one JSON object for each row, for other tools.
#
# Exit codes: 0 = traces found. 1 = error, or TRACE: NOT_FOUND (the session has no
# traces, but other agent spans exist). 2 = usage. 3 = TRACE: NOT_APPLICABLE (no
# agent in the project has ADK spans in Cloud Trace).
#
# The starter pack agent runs `adk api_server --trace_to_cloud`, but on 12 Nov 2026
# its span export failed with INVALID_ARGUMENT "Invalid project id in name!"
# (backlog item 36). Until that is fixed, expect NOT_APPLICABLE for it.
#
# Read-only. It uses the Cloud Trace API v1 (projects.traces.list and get).
# Cloud Trace API v2 can only write spans. The request bills the target project
# for quota (x-goog-user-project). Without this header, the shared gcloud client
# project can return 429 RESOURCE_EXHAUSTED.
#
# How to read a denied tool call: when the egress gateway denies a tools/call
# (for example an IAP policy denial), the trace has the execute_tool span with an
# error in tool_response, and no Model Armor or MCP server span below it. ADK
# reports the 403 as "MCP session connection lost". The script marks this row as
# NO_DOWNSTREAM. This is evidence, not proof: use the gateway request log
# (scripts/read_audit_log.sh) to confirm the 403.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud python3

usage() {
  sed -n '6,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 2
}

SESSION=""
TRACE=""
SINCE="7d"
PROJECT=""
JSON="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --trace) TRACE="${2:?--trace needs a TRACE_ID}"; shift 2 ;;
    --since) SINCE="${2:?--since needs a value, for example 24h}"; shift 2 ;;
    --project) PROJECT="${2:?--project needs a PROJECT_ID}"; shift 2 ;;
    --json) JSON="true"; shift ;;
    -h|--help) usage ;;
    -*) echo "ERROR: unknown flag $1" >&2; usage ;;
    *) SESSION="$1"; shift ;;
  esac
done
if [[ -z "${SESSION}" && -z "${TRACE}" ]]; then
  usage
fi
if [[ -z "${PROJECT}" ]]; then
  need terraform
  PROJECT="$(tf_output project_id)"
fi

TOKEN="$(gcloud auth print-access-token)"

TOKEN="${TOKEN}" python3 - "${PROJECT}" "${SESSION}" "${TRACE}" "${SINCE}" "${JSON}" <<'PY'
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

project, session, trace_id, since, as_json = sys.argv[1:6]
as_json = as_json == "true"
token = os.environ["TOKEN"]
base = f"https://cloudtrace.googleapis.com/v1/projects/{project}/traces"
sgt = dt.timezone(dt.timedelta(hours=8))


def call(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project,
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        body = err.read().decode(errors="replace")
        try:
            msg = json.loads(body)["error"]["message"]
        except (ValueError, KeyError):
            msg = body[:300]
        sys.exit(f"ERROR: Cloud Trace API returned {err.code}: {msg}")


def parse_time(value):
    # RFC 3339 with up to 9 fraction digits. Python reads 6 digits.
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z", value)
    frac = (m.group(2) or ".0")[:7].ljust(7, "0")
    return dt.datetime.strptime(m.group(1) + frac, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=dt.timezone.utc)


def since_start(value):
    m = re.fullmatch(r"(\d+)([mhd])", value)
    if not m:
        sys.exit("ERROR: --since must look like 30m, 12h, or 7d")
    unit = {"m": "minutes", "h": "hours", "d": "days"}[m.group(2)]
    start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(**{unit: int(m.group(1))})
    return start.strftime("%Y-%m-%dT%H:%M:%SZ")


def short(value, size=70):
    value = " ".join(str(value).split())
    return value if len(value) <= size else value[: size - 3] + "..."


def trace_ids_for_session():
    ids, page = [], ""
    while True:
        query = {
            "filter": f"+gen_ai.conversation.id:{session}",
            "startTime": since_start(since),
            "view": "ROOTSPAN",
            "pageSize": "100",
        }
        if page:
            query["pageToken"] = page
        data = call(base + "?" + urllib.parse.urlencode(query))
        for t in data.get("traces", []):
            start = min(parse_time(s["startTime"]) for s in t.get("spans", [])) if t.get("spans") else None
            ids.append((start, t["traceId"]))
        page = data.get("nextPageToken", "")
        if not page:
            break
    return [tid for _, tid in sorted(ids, key=lambda x: x[0] or dt.datetime.min.replace(tzinfo=dt.timezone.utc))]


def rows_for_trace(tid):
    spans = call(f"{base}/{tid}").get("spans", [])
    children = {}
    for s in spans:
        children.setdefault(s.get("parentSpanId"), []).append(s)

    def descendants(span_id):
        out, todo = [], list(children.get(span_id, []))
        while todo:
            s = todo.pop()
            out.append(s)
            todo.extend(children.get(s["spanId"], []))
        return out

    rows = []
    for s in sorted(spans, key=lambda x: x["startTime"]):
        name, lab = s["name"], s.get("labels", {})
        row = None
        if name.startswith("invoke_agent"):
            row = ("AGENT", name, "", lab.get("gen_ai.agent.name", ""))
        elif name.startswith("generate_content"):
            row = ("MODEL", lab.get("gen_ai.request.model", name), "",
                   f"tokens in={lab.get('gen_ai.usage.input_tokens', '?')} out={lab.get('gen_ai.usage.output_tokens', '?')}")
        elif name.startswith("execute_tool"):
            tool = lab.get("gen_ai.tool.name", name.split(" ", 1)[-1])
            resp = lab.get("gcp.vertex.agent.tool_response", "")
            below = descendants(s["spanId"])
            reached = any(d["name"] in ("Request Path", "/mcp") or d["name"].startswith("tools/call") for d in below)
            # With trace_message_content = false (default), the span has no tool
            # response. Then a client "MCP send tools/call" span with no gateway or
            # MCP server span below it shows that the call did not reach the server
            # (live, 14 Nov 2026: an IAP ENFORCE denial).
            sent = any(d["name"].startswith("MCP send tools/call") for d in below)
            failed = '"error"' in resp or (not resp and sent and not reached)
            if failed and not reached:
                result = "NO_DOWNSTREAM"
                detail = "Error, and no gateway or MCP span below it. Check the gateway log for a 403. " + short(resp, 60)
            elif failed:
                result = "ERROR"
                detail = short(resp, 80)
            else:
                result = "OK"
                detail = "args=" + short(lab.get("gcp.vertex.agent.tool_call_args", ""), 60)
            row = ("TOOL", tool, result, detail)
        elif name in ("Request Path", "Response Path") and lab.get("service.name") == "modelarmor":
            where = "prompt" if name == "Request Path" else "response"
            decision = lab.get("gen_ai.security.decision.type", "?")
            detail = f"{lab.get('gen_ai.security.policy.name', '')} {lab.get('gcp.modelarmor.filter.match.state', '')}"
            extra = lab.get("gcp.modelarmor.violations") or lab.get("gcp.modelarmor.sdp.info_types")
            if extra:
                detail += " " + short(extra, 50)
            row = ("MODEL_ARMOR", f"gateway {where} check", f"{decision.upper()} {lab.get('gen_ai.security.decision.code', '')}".strip(), detail.strip())
        elif name == "/mcp" and "/http/status_code" in lab:
            row = ("MCP_HTTP", lab.get("/http/host", name), lab["/http/status_code"], lab.get("faas.name", ""))
        elif name.startswith("tools/call"):
            row = ("MCP_SERVER", name, "", f"tool={lab.get('mcp.tool.name') or lab.get('gen_ai.tool.name', '')} session={lab.get('mcp.session.id', '')}")
        if row:
            rows.append((parse_time(s["startTime"]).astimezone(sgt), tid) + row)
    return rows, len(spans)


tids = [trace_id] if trace_id else trace_ids_for_session()
if not tids:
    # Find out if any agent in the project sends ADK spans in the same window.
    probe = call(base + "?" + urllib.parse.urlencode({
        "filter": "+gen_ai.operation.name:invoke_agent",
        "startTime": since_start(since),
        "view": "MINIMAL",
        "pageSize": "1",
    }))
    if not probe.get("traces"):
        print(f"TRACE: NOT_APPLICABLE (no agent spans in project {project} in the last {since}. "
              "No agent span reached Cloud Trace. Look in the agent log for 'Error while writing to "
              "Cloud Trace'. Use scripts/read_audit_log.sh for the gateway evidence.)")
        sys.exit(3)
    sys.exit(f"TRACE: NOT_FOUND (no traces for session {session} in the last {since} in project {project}. "
             "Other agent spans exist. Check the session ID, or wait 1 to 2 minutes for new spans.)")

all_rows = []
for tid in tids:
    rows, count = rows_for_trace(tid)
    all_rows.extend(rows)
    if as_json:
        continue
    first = rows[0][0].strftime("%Y-%m-%d %H:%M:%S SGT") if rows else "?"
    print(f"== Trace {tid}  start {first}  spans {count} ==")
    print(f"{'TIME_SGT':<12} {'LAYER':<12} {'SPAN':<40} {'RESULT':<14} DETAIL")
    for t, _, layer, span, result, detail in rows:
        print(f"{t.strftime('%H:%M:%S.%f')[:12]:<12} {layer:<12} {short(span, 40):<40} {result:<14} {detail}")
    print()

if as_json:
    for t, tid, layer, span, result, detail in all_rows:
        print(json.dumps({"time_sgt": t.strftime("%Y-%m-%d %H:%M:%S.%f SGT"), "trace_id": tid, "layer": layer,
                          "span": span, "result": result, "detail": detail}))
    sys.exit(0)

tools = [r for r in all_rows if r[2] == "TOOL"]
blocked = [r for r in all_rows if r[2] == "MODEL_ARMOR" and not r[4].startswith("ALLOW")]
bad_http = [r for r in all_rows if r[2] == "MCP_HTTP" and not str(r[4]).startswith("2")]
print("== Summary ==")
print(f"Traces: {len(tids)}. Tool calls: {len(tools)}. "
      f"Tool errors: {sum(1 for r in tools if r[4] != 'OK')}, of which NO_DOWNSTREAM: {sum(1 for r in tools if r[4] == 'NO_DOWNSTREAM')}. "
      f"Model Armor checks that block or modify: {len(blocked)}. MCP HTTP responses not 2xx: {len(bad_http)}.")
PY
