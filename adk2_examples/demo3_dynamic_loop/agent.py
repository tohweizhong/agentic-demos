import asyncio
from typing import Any
from google.adk import Workflow, Event
from google.adk.workflow import node
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

# Mocked Agents and Functions for Demo Purposes
coder_agent = LlmAgent(
    name="coder",
    model="gemini-2.5-flash",
    instruction="Write Python code for the user's request. Return only the python code block."
)

fixer_agent = LlmAgent(
    name="fixer",
    model="gemini-2.5-flash",
    instruction="Fix the provided code based on the findings. Return only the python code block."
)

# Mocked Checker Function
first_run = True
def compile_lint_check(code):
    global first_run
    class CheckResult:
        def __init__(self, findings):
            self.findings = findings
            
    if first_run:
        first_run = False
        return CheckResult(findings="Error: Missing comments explaining the code")
    return CheckResult(findings=None)

def extract_text(content):
    if hasattr(content, 'parts') and content.parts:
        return "".join([part.text for part in content.parts if part.text])
    return str(content)

# 1. Define the Dynamic Workflow Node
@node(rerun_on_resume=True)
async def code_workflow(ctx: Any, node_input: types.Content):
    user_request = extract_text(node_input)
    print(f"--- Running Coder Agent with request: {user_request} ---")
    code = await ctx.run_node(coder_agent, user_request)
    code_text = extract_text(code)
    check_resp = compile_lint_check(code_text)
    
    # Loop continues until no findings/errors are returned
    while check_resp.findings:
        print(f"Findings Detected: {check_resp.findings}")
        yield Event(state={"code": code_text, "findings": check_resp.findings})
        
        print("--- Running Fixer Agent ---")
        code = await ctx.run_node(fixer_agent, {"code": code_text, "findings": check_resp.findings})
        code_text = extract_text(code)
        
        check_resp = compile_lint_check(code_text)
        
    print("--- Code Verified Successfully ---")
    yield Event(output=code_text)


# 2. Define Root Agent
root_agent = code_workflow

# 3. Runner Execution Setup
async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="Demo3_DynamicLoop",
        agent=root_agent, # Using the root agent
        session_service=session_service
    )
    
    session = await session_service.create_session(app_name="Demo3_DynamicLoop", user_id="user_1")
    
    user_content = types.Content(parts=[types.Part.from_text(text="Write a script to say hello")])
    print("User Request: Write a script to say hello\n")
    
    async for event in runner.run_async(session_id=session.id, user_id="user_1", new_message=user_content):
        if event.message:
            print(f"Final Agent Output: {event.message.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
