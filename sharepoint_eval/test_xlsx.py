import asyncio
import sys
import os

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
    print("Initializing Agent Runner for XLSX Testing...")
    session_service = InMemorySessionService()
    runner = Runner(agent=agent.root_agent, session_service=session_service, app_name="sharepoint_file_lister", auto_create_session=True)
    session_id = "xlsx_session"
    
    # 1. Locate the unencrypted XLSX file
    await send_query(runner, "Locate the file 7-day Moving Average Daily Estimated Numbers of COVID-19 Infections.xlsx", session_id)
    
    # 2. Ask a question requiring direct data extraction and comparison insight (weekends vs weekdays)
    await send_query(runner, "Read the table contents. Tell me what columns are in this file and give me an insight: looking at the data, do infection numbers tend to be higher or lower on weekends/holidays (where the holiday column is 1) compared to weekdays (0)?", session_id)

if __name__ == "__main__":
    asyncio.run(main())
