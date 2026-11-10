"""Sample 3: traces (ADK with OpenTelemetry) on Agent Runtime.

The agent runs with GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true, so ADK
writes a trace for each request. The tool get_service_status adds a custom
span and returns its trace ID. This sample sends one query and prints the
trace ID and a Cloud Trace link.

Usage: python samples/3_o11y.py
"""

import uuid

from common import ask, cloud_trace_link, get_runtime, session_id, step, trace_ids_from_events

USER_ID = f"sample-user-{uuid.uuid4().hex[:8]}"


def main():
  settings, _, runtime = get_runtime()
  print(f"Agent: {settings.agent_runtime_name}")

  step("1. Send one query that uses the tool")
  sid = session_id(runtime.create_session(user_id=USER_ID))
  events = ask(runtime, USER_ID, sid, "What is the status of the search service?")

  step("2. Find the trace")
  trace_ids = trace_ids_from_events(events)
  if not trace_ids:
    print("  The model did not call get_service_status. Run the sample again.")
    return
  for trace_id in trace_ids:
    print(f"  trace_id = {trace_id}")
    print(f"  Cloud Trace: {cloud_trace_link(settings.project_id, trace_id)}")
  print("  The trace has the ADK spans and the custom span get_service_status.")
  print("  Traces can take one or two minutes to show.")

  step("3. Check where the traces are stored")
  print("  Run this command. The _Trace bucket must be in the region:")
  print(
      f"    gcloud observability buckets list --project={settings.project_id} "
      f"--location={settings.region}"
  )
  print("  Also check the agent logs for this error from the trace exporter:")
  print('    "400 Invalid project id in name!"')


if __name__ == "__main__":
  main()
