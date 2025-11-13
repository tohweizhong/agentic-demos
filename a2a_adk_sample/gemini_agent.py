
import os
from google.adk.agents import LlmAgent
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from google.adk.tools import FunctionTool

# --- DEFINE YOUR TOOLS HERE ---
def get_weather(location: str) -> str:
    """Gets the weather for a given location."""
    # In a real scenario, you might call a weather API here.
    return f"The weather in {location} is always sunny!"


class GeminiAgent(LlmAgent):
    """An agent powered by the Gemini model via Vertex AI."""

    # --- AGENT IDENTITY ---
    # These are the default values. The notebook can override them.
    name: str = "gemini_agent"
    description: str = "A helpful assistant powered by Gemini."

    def __init__(self, **kwargs):
        print("Initializing GeminiAgent...")
        # --- SET YOUR SYSTEM INSTRUCTIONS HERE ---
        instructions = """
        You are a helpful and friendly assistant. Your task is to answer user queries using puns, if a city is mentioned, answer in the language spoken there. 

        You can use the weather tool to find the weather in a location.
        """
        

        # --- REGISTER YOUR TOOLS HERE ---
        tools = [
            get_weather
        ]

        super().__init__(
            model=os.environ.get("MODEL", "gemini-2.5-flash"),
            instruction=instructions,
            tools=tools,
            **kwargs,
        )


    def create_agent_card(self, agent_url: str) -> "AgentCard":
        return AgentCard(
            
name=self.name,
            description=self.description,
            url=agent_url,
            version="1.0.0",
            defaultInputModes=["text/plain"],
            defaultOutputModes=["text/plain"],
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="chat",
                    name="Chat Skill",
                    description="Chat with the Gemini agent.",
                    tags=["chat"],
                    examples=["Hello, world!"]
                )
            ]

        )
