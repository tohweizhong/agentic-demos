import os
from dotenv import load_dotenv
from agent import root_agent
import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

load_dotenv()

# Load environment variables
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GOOGLE_CLOUD_LOCATION")
project_number = os.environ.get("PROJECT_NUMBER")
currency_exchange_key = os.environ.get("CURRENCY_EXCHANGE_API_KEY")

env_vars = {
    "GOOGLE_GENAI_USE_VERTEXAI": "1",
    "PROJECT_NUMBER": str(project_number),
    "CURRENCY_EXCHANGE_API_KEY": str(currency_exchange_key) ,
}

# Initialize Vertex AI
vertexai.init(
    project=project_id,
    location=location,
    staging_bucket=f"gs://{project_id}-labconfig-bucket",
)

# Create the app and agent
app = AdkApp(agent=root_agent)

# Deploy remote agent
remote_agent = agent_engines.create(
    app,
    requirements=[
        "google-cloud-aiplatform[agent_engines,adk]",
        "a2a-sdk",
    ],
    env_vars=env_vars,
    extra_packages=["shared"],
    display_name="campaign-orchestrator",
    description=(
        "The CampaignOrchestrator is a coordination agent that delegates tasks via A2A protocol and synthesizes responses into a complete marketing campaign."
    ),
)

# Query the agent
query = "ChronoLeap Smartwatch in Japan and my budget is 200 USD?"
for event in remote_agent.stream_query(user_id="cepfuser", message=query):
    print(event)
