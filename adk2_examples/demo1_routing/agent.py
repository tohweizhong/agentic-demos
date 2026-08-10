import asyncio
from google.adk import Workflow
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

# 1. Define the Nodes

# Classifier Agent
classifier = LlmAgent(
    name="classifier",
    model="gemini-2.5-flash",
    instruction="""Classify user message into "BUG", "CUSTOMER_SUPPORT", or "LOGISTICS". 
If message applies to more than one category, reply with a comma-separated list of categories.""",
)

# Router Function
def router(node_input: str):
    # Extracts the classification result and determines the route
    routes = node_input.split(",")
    routes = [route.strip() for route in routes]
    # Yield an event with the specific route(s)
    yield Event(route=routes)

# Handlers (Mocked as simple functions, but could be LlmAgents)
def bug_handler():
    yield types.ModelContent("Handling bug...")

def customer_support_handler():
    yield types.ModelContent("Handling customer support...")

def logistics_handler():
    yield types.ModelContent("Handling logistics...")

# 2. Define the Graph Flow (Workflow)
root_agent = Workflow(
    name="routing_workflow",
    edges=[
        ("START", classifier),
        (classifier, router),
        (router, {
            "BUG": bug_handler,
            "CUSTOMER_SUPPORT": customer_support_handler,
            "LOGISTICS": logistics_handler,
        }),
    ],
)

# 3. Runner Execution Setup
async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="Demo1_RoutingApp",
        agent=root_agent,
        session_service=session_service
    )
    
    # Create a session
    session = await session_service.create_session(
        app_name="Demo1_RoutingApp", 
        user_id="user_1"
    )
    
    # Send a message
    user_content = types.Content(parts=[types.Part.from_text(text="I need to report a bug and check my shipping status.")])
    print("User: I need to report a bug and check my shipping status.\n")
    
    async for event in runner.run_async(session_id=session.id, user_id="user_1", new_message=user_content):
        if event.message:
            print(f"Agent Output: {event.message.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
