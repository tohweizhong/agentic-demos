import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import agent

async def send_query(runner, user_query: str, session_id: str):
    print(f"\n========================================\nUSER: {user_query}\n========================================")
    print("Thinking...")
    
    content = types.Content(role='user', parts=[types.Part(text=user_query)])
    final_text = ""
    try:
        async for event in runner.run_async(
            new_message=content,
            user_id="test_user",
            session_id=session_id
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_text = event.content.parts[0].text
        print(f"AGENT:\n{final_text}")
    except Exception as e:
        print(f"Error occurred: {e}")

async def main():
    print("Initializing Agent Runner for PPTX Testing...")
    session_service = InMemorySessionService()
    runner = Runner(agent=agent.root_agent, session_service=session_service, app_name="sharepoint_file_lister", auto_create_session=True)
    session_id = "pptx_session"
    
    # 1. Locate the unencrypted PPTX file
    await send_query(runner, "Locate the file Corporate transactions.pptx", session_id)
    
    # 2. Ask a slide-specific detail extraction question
    await send_query(runner, "List the three key platforms for corporate transactions described in the slides and explain what Corppass does", session_id)

if __name__ == "__main__":
    asyncio.run(main())
