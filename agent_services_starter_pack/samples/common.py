"""Helpers that the three samples use.

The samples call the deployed agent. The agent returns events as dicts. These
helpers read the parts of the events that the samples print.
"""

import sys
import pathlib

# Lets the samples import config.py from the pack folder.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import config  # pylint: disable=wrong-import-position


def _get(obj, key, default=None):
  """Reads a key from a dict, or an attribute from an object."""
  if isinstance(obj, dict):
    return obj.get(key, default)
  return getattr(obj, key, default)


def _parts(event):
  content = _get(event, "content") or {}
  return _get(content, "parts") or []


def event_text(event):
  """Returns the text parts of one event, joined."""
  return "".join(_get(part, "text") or "" for part in _parts(event))


def final_text(events):
  """Returns the text of the last event that has text."""
  for event in reversed(events):
    text = event_text(event)
    if text:
      return text
  return ""


def function_responses(events):
  """Returns (tool name, response) for each tool result in the events."""
  results = []
  for event in events:
    for part in _parts(event):
      response = _get(part, "function_response")
      if response:
        results.append((_get(response, "name"), _get(response, "response")))
  return results


def trace_ids_from_events(events):
  """Returns the trace IDs that get_service_status put in its results."""
  ids = []
  for _, response in function_responses(events):
    trace_id = _get(response or {}, "trace_id")
    if trace_id:
      ids.append(trace_id)
  return ids


def cloud_trace_link(project_id, trace_id):
  """Returns a Cloud Trace Explorer link for one trace. Not tested."""
  return (
      f"https://console.cloud.google.com/traces/explorer;traceId={trace_id}"
      f"?project={project_id}"
  )


def memory_scope(runtime_id, user_id):
  """Returns the Memory Bank scope that ADK uses on Agent Runtime.

  On Agent Runtime, the ADK app name is the Agent Runtime ID.
  """
  return {"app_name": runtime_id, "user_id": user_id}


def memory_fact(retrieved):
  """Returns the fact text of one retrieved memory."""
  return _get(_get(retrieved, "memory"), "fact") or ""


def event_summary(event):
  """Returns "author: part types" for one event, for a short event list."""
  kinds = []
  for part in _parts(event):
    if _get(part, "text"):
      kinds.append("text")
    elif _get(part, "function_call"):
      kinds.append(f"function_call({_get(_get(part, 'function_call'), 'name')})")
    elif _get(part, "function_response"):
      kinds.append(
          f"function_response({_get(_get(part, 'function_response'), 'name')})"
      )
  return f"{_get(event, 'author')}: {', '.join(kinds) or 'no content'}"


def session_id(session):
  """Returns the ID of a session in dict or object form."""
  return _get(session, "id")


def get_runtime():
  """Returns the settings and the deployed Agent Runtime object."""
  import agentplatform  # pylint: disable=import-outside-toplevel

  settings = config.load_settings()
  name = settings.require_runtime_name()
  client = agentplatform.Client(project=settings.project_id, location=settings.region)
  return settings, client, client.runtimes.get(name=name)


def ask(runtime, user_id, session, message):
  """Sends one message in one session. Prints and returns the events."""
  print(f"\n  user> {message}")
  events = list(
      runtime.stream_query(user_id=user_id, session_id=session, message=message)
  )
  print(f"  agent> {final_text(events)}")
  return events


def step(text):
  """Prints a step heading."""
  print(f"\n== {text}")
