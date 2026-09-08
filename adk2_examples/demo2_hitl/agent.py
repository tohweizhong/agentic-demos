import asyncio
from google.adk import Workflow
from google.adk.events import RequestInput
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

# 1. Define the Nodes
def ask_number():
    # Human input step: Workflow is suspended here
    yield RequestInput(message="Enter a number:")

def multiply_number(node_input):
    # This node executes once the user provides input
    try:
        number = int(node_input)
    except (ValueError, TypeError):
        number = 0
    result = number * 2
    yield types.ModelContent(f"The result of {number} * 2 is {result}")

# 2. Define the Workflow
root_agent = Workflow(
    name="hitl_workflow",
    edges=[('START', ask_number, multiply_number)],
)

# 3. Runner Execution Setup
async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="Demo2_HITL",
        agent=root_agent,
        session_service=session_service
    )
    
    session = await session_service.create_session(app_name="Demo2_HITL", user_id="user_1")
    
    # Start workflow
    print("--- Starting Workflow ---")
    start_content = types.Content(parts=[types.Part.from_text(text="start")])
    interrupt_id = None
    async for event in runner.run_async(session_id=session.id, user_id="user_1", new_message=start_content):
        for fc in event.get_function_calls():
            if fc.name == 'adk_request_input':
                interrupt_id = fc.id
                print(f"Agent Request: {fc.args.get('message')}")
            
    # Simulate user providing input
    user_input = "5"
    print(f"User Input: {user_input}\n")
    
    if not interrupt_id:
        print("Error: Workflow was not suspended with RequestInput.")
        return
        
    # Build FunctionResponse content to resume
    user_response_part = types.Part(
        function_response=types.FunctionResponse(
            name="adk_request_input",
            id=interrupt_id,
            response={"result": user_input}
        )
    )
    user_content = types.Content(parts=[user_response_part])
    
    # Resume workflow
    async for event in runner.run_async(session_id=session.id, user_id="user_1", new_message=user_content):
        if event.message:
            print(f"Agent Output: {event.message.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
