import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    print("Initializing Agent Runner...")
    session_service = InMemorySessionService()
    runner = Runner(agent=agent.root_agent, session_service=session_service, app_name="sharepoint_file_lister", auto_create_session=True)
    
    session_id = "test_session_1"
    
    # Step 1: Locate the file
    await send_query(runner, "Locate the file test2.docx", session_id)
    
    # Step 2: Summarize its contents
    await send_query(runner, "Summarize its contents", session_id)

    # Step 3: Clarify which copy to read
    await send_query(runner, "Use the one in SDP tests/test2.docx", session_id)

if __name__ == "__main__":
    asyncio.run(main())
