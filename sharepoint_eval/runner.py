import asyncio
import sys
import os
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import agent

async def query_agent(runner, user_query: str):
    print(f"\nSending query: '{user_query}' to agent...")
    print("Thinking... (running tools if needed)")
    
    content = types.Content(role='user', parts=[types.Part(text=user_query)])
    
    try:
        async for event in runner.run_async(
            new_message=content,
            user_id="default_user",
            session_id="default_session"
        ):
            # Check if event is final response or has content
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    print("\n==================== Agent Response ====================")
                    print(final_response)
                    print("========================================================\n")
                else:
                    print("\n==================== Agent Response ====================")
                    print("Agent execution finished with no content.")
                    print("========================================================\n")
            elif hasattr(event, 'content') and event.content and event.content.parts:
                # This could be intermediate tool execution logs or streaming tokens
                part_text = event.content.parts[0].text
                if part_text and not event.is_final_response():
                    # Print intermediate thoughts or tool logs silently or with a prefix
                    pass
    except Exception as e:
        print(f"\nAn error occurred while running the agent: {str(e)}")
        if "api_key" in str(e).lower() or "credentials" in str(e).lower():
            print("\n[Tip] Please make sure you have set your Gemini API Key or Google Cloud Credentials.")
            print("For example, you can run: export GEMINI_API_KEY='your-api-key'")

async def main():
    # Initialize the ADK Runner with our root agent and session service
    # This runner manages state, calls the LLM, and executes tools
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent.root_agent,
        session_service=session_service,
        app_name="sharepoint_file_lister",
        auto_create_session=True
    )
    
    # If user passed command line arguments, run that query
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        await query_agent(runner, query)
    else:
        # Interactive loop
        print("========================================================")
        print("      SharePoint File Lister - ADK Agent CLI")
        print("========================================================")
        print("Enter your query (e.g., 'List all files in the root folder')")
        print("Type 'exit' or 'quit' to end the chat.\n")
        
        while True:
            try:
                user_query = input("You > ")
                if user_query.strip().lower() in ["exit", "quit"]:
                    print("Goodbye!")
                    break
                if not user_query.strip():
                    continue
                await query_agent(runner, user_query)
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break

if __name__ == "__main__":
    # ADK is asynchronous, so we run the main function within the event loop
    asyncio.run(main())
