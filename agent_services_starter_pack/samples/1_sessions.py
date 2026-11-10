"""Sample 1: Sessions on Agent Runtime.

A session holds the events of one conversation. Agent Runtime stores them in
Sessions in the region of the agent. This sample creates a session, sends two
turns, resumes the session with a third turn, and lists the events.

Usage: python samples/1_sessions.py
"""

import uuid

from common import ask, event_summary, get_runtime, session_id, step

USER_ID = f"sample-user-{uuid.uuid4().hex[:8]}"


def main():
  settings, _, runtime = get_runtime()
  print(f"Agent: {settings.agent_runtime_name}")
  print(f"User:  {USER_ID}")

  step("1. Create a session")
  session = runtime.create_session(user_id=USER_ID)
  sid = session_id(session)
  print(f"  session_id = {sid}")

  step("2. Send two turns in the session")
  ask(runtime, USER_ID, sid, "My team owns the payments service.")
  ask(runtime, USER_ID, sid, "What is the status of my team's service?")

  step("3. Resume the session. The agent sees the earlier turns")
  ask(runtime, USER_ID, sid, "Which service did I say that my team owns?")

  step("4. List the events in the session")
  stored = runtime.get_session(user_id=USER_ID, session_id=sid)
  events = stored.get("events", []) if isinstance(stored, dict) else stored.events
  print(f"  {len(events)} events are stored in Sessions:")
  for event in events:
    print(f"   - {event_summary(event)}")

  step("5. List the sessions of the user")
  listed = runtime.list_sessions(user_id=USER_ID)
  sessions = listed.get("sessions", []) if isinstance(listed, dict) else listed.sessions
  for item in sessions:
    print(f"   - {session_id(item)}")

  print(
      "\nResult: the third answer uses facts from the first turn. Sessions "
      "stored the events between the calls."
  )


if __name__ == "__main__":
  main()
