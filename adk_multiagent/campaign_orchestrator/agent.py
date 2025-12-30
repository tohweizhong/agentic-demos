import os
from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()


try:
    # Absolute imports — work in Agent Engine
  from shared.client import A2AToolClient 

except ImportError:
  # Relative imports — work locally with `adk web`
  from .shared.client import A2AToolClient

from google.cloud import logging

# Initialize the client
client = logging.Client()

# Create a custom logger for activity tracking
logger = client.logger("cepf-tracking-log-campaign-orchestrator") 

a2a_client = A2AToolClient()

region = os.environ.get("GOOGLE_CLOUD_LOCATION") 
project_number = os.environ.get("PROJECT_NUMBER")


creative_director_url = f"https://creative-director-{project_number}.{region}.run.app"
financial_analyst_url = f"https://financial-analyst-{project_number}.{region}.run.app"

########################################################################################################################################
# TODO 1: Add remote agents url for creative director and financial analyst agent deployed on Cloud Run and in the A2AToolClient object 
# Use add_remote_agent method to add agents url
# Pass list_remote_agents and create task method as tools to the campaign_orchestrator agent for A2A communication.
########################################################################################################################################

a2a_client.add_remote_agent(creative_director_url)
a2a_client.add_remote_agent(financial_analyst_url)

campaign_orchestrator = Agent(
    model="gemini-2.5-pro",
    name="campaign_orchestration_host",
    description="Orchestrates multi-agent marketing campaign generation via A2A communication.",
    instruction="""
You are a Host Orchestrator AI responsible for coordinating with remote agents to generate a complete marketing campaign.

You must NOT generate any content yourself. Your role is strictly to delegate tasks and compile results.

Tools Available:
- a2a_client.list_remote_agents()
- a2a_client.create_task(url, payload)

Workflow:

1. Parse the user input to extract:
   - product name
   - target country
   - budget (in USD)

2. Use `a2a_client.list_remote_agents()` to retrieve available agent URLs.
   - Identify the URLs for:
     - `creative_director_agent`
     - `financial_analyst_agent`

3. Call `creative_director_agent` with:
   - Payload: product name and target country
   - Save the result as `generate_campaign_content`

4. Wait for `creative_director_agent` to complete before proceeding.

5. Once done, call `financial_analyst_agent` with:
   - Payload: target country
   - Save the result as `estimate_budget`

6. After both responses are received, combine them into the final JSON output in the exact structure below.
   - Do not include any additional text or metadata in your output.
   - All required fields must be present.

Final Output Format:
{
  "product_name": "<product>",
  "target_country": "<country>",
  "campaign_slogan": "...",
  "target_demographic": {
    "age_group": "...",
    "interests": ["...", "..."]
  },
  "key_messages": [
    "...",
    "...",
    "..."
  ],
  "budget": {
    "currency": "",
    "amount": 
  },
  "image_url": "gs://..."
}
""",
    tools=[
        a2a_client.list_remote_agents,
        a2a_client.create_task
    ]
)


# Do not change — used for activity tracking.
logger.log_text(
    f"a2a: {a2a_client.list_remote_agents()}"
)

# Required for ADK runtime
root_agent = campaign_orchestrator