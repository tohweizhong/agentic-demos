"""Sample 2: Memory Bank on Agent Runtime.

Memory Bank keeps facts about a user across sessions. The agent sends the
session events to Memory Bank after each turn. Memory Bank generates the
memories in the background. In a new session, PreloadMemoryTool gives the memories to the model.

Usage: python samples/2_memory_bank.py
"""

import time
import uuid

from common import ask, get_runtime, memory_fact, memory_scope, session_id, step

USER_ID = f"sample-user-{uuid.uuid4().hex[:8]}"
WAIT_SECONDS = 180
POLL_SECONDS = 10

RESIDENCY_WARNING = """\
DATA RESIDENCY in asia-southeast1:
  - Memories are stored in the region of the agent (data at rest).
  - Memory generation uses the model in MEMORY_GENERATION_MODEL. gemini-3.5-flash
    has ML processing in Singapore.
  - Similarity search uses the model in EMBEDDING_MODEL. No Google embedding model
    has ML processing in Singapore. This step is processed outside Singapore.
"""


def retrieve_memories(client, settings):
  scope = memory_scope(settings.runtime_id, USER_ID)
  return list(
      client.memory_banks.memories.retrieve(
          name=settings.agent_runtime_name, scope=scope
      )
  )


def main():
  settings, client, runtime = get_runtime()
  print(RESIDENCY_WARNING)
  print(f"Agent: {settings.agent_runtime_name}")
  print(f"User:  {USER_ID}")
  print(f"Embedding model: {settings.embedding_model_resource}")

  step("1. Session A: tell the agent some facts")
  session_a = session_id(runtime.create_session(user_id=USER_ID))
  ask(
      runtime,
      USER_ID,
      session_a,
      "Please remember this: my name is Alex, I am on call for the payments "
      "service this week, and I prefer short answers in bullet points.",
  )

  step(f"2. Wait for Memory Bank to generate memories (up to {WAIT_SECONDS} s)")
  memories = []
  deadline = time.monotonic() + WAIT_SECONDS
  while time.monotonic() < deadline:
    memories = retrieve_memories(client, settings)
    if memories:
      break
    print(f"  no memories yet, next check in {POLL_SECONDS} s")
    time.sleep(POLL_SECONDS)
  if not memories:
    print("  No memories after the wait. Check the agent logs for Memory Bank errors.")
    return
  print(f"  {len(memories)} memories for this user:")
  for item in memories:
    print(f"   - {memory_fact(item)}")

  step("3. Session B: a new session. The agent gets the memories")
  session_b = session_id(runtime.create_session(user_id=USER_ID))
  print(f"  session A = {session_a}")
  print(f"  session B = {session_b}")
  ask(runtime, USER_ID, session_b, "What do you know about me and my on-call duty?")

  print(
      "\nResult: session B has none of the events of session A. The answer "
      "comes from Memory Bank."
  )


if __name__ == "__main__":
  main()
