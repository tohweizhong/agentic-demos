from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search, FunctionTool
from google.cloud import storage
from urllib.parse import urlparse
from google.adk.agents import Agent
import os
from google.cloud import logging
from dotenv import load_dotenv

load_dotenv()


# Initialize the client
client = logging.Client()

# Create a custom logger for activity tracking
logger = client.logger("cepf-tracking-log-market-researcher") 


project_id = os.environ["GOOGLE_CLOUD_PROJECT"]

# --- TOOL: GCS Reader Tool ---
# def read_gcs_file(gcs_uri: str) -> dict:
def read_gcs_file() -> dict:  
    parsed = urlparse(f"gs://{project_id}-labconfig-bucket/product_brief.txt")
    bucket_name = parsed.netloc
    blob_name = parsed.path.lstrip("/")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    content = blob.download_as_text()
    return {"status": "success", "content": content}

##############################################################################################################################
# TODO 1: Pass the read_gcs_file function to the agent as FunctionTool so it can access product brief data from Cloud Storage.
##############################################################################################################################

gcs_reader_tool = FunctionTool(func=read_gcs_file)

gcs_agent = Agent(
    name="ReadGCSAgent",
    model="gemini-2.5-pro",
    description="Reads product brief from GCS and extracts key features.",
    instruction="""

1. Call `gcs_reader_tool`. Save the result as `content`.

2. From the `content`, extract 3-5 key product features.

Respond with:
{
  "key_features": ["...", "..."]
}
""",
    tools=[gcs_reader_tool],
    output_key="key_features"
)

##################################################################################################
# TODO 2: Integrate the built in tool so the agent can perform web searches through Google Search.
##################################################################################################

search_agent = Agent(
    name="SearchAgent",
    model="gemini-2.5-pro",
    description="Searches for fashion trends and smartwatch competitors.",
    instruction="""
You are a trend researcher. You get input like:
Extract country and product from user query.

{
  "product": "",
  "country": ""
}

Use Google Search Tool to run based on {key_features}:
- "latest {key_features} in country (you have to take country from responce)"
- "{key_features} competitors in country (you have to take country from responce)"

Respond with:
{
  "trends": [...],
  "competitors": [...]
}
""",
    tools=[google_search],
    output_key="search_results"
)


# --- STEP 3: Controller Agent (Final Output Composer) ---
controller_agent = Agent(
    name="ControllerAgent",
    model="gemini-2.5-pro",
    description="Combines GCS and search results into one final JSON.",
    instruction="""
You are given:
1. key_features from GCS agent:
   {key_features}

2. search_results from the SearchAgent:
   {search_results}

Now compose and return:
{
  "key_features": [...],
  "trends": [...],
  "competitors": [...]
}
Only return the JSON object.
""",
    output_key="market_context"
)

# --- Sequential Agent Pipeline ---
market_researcher_agent = SequentialAgent(
    name="market_research_controller_agent",
    description="Combines internal GCS product insight with market trends using sequential agent pipeline.",
    sub_agents=[gcs_agent, search_agent, controller_agent],
    # output_key="market_researcht_responce"
)

# Do not change — used for activity tracking.
logger.log_text(
    f"gcs_agent.tools: {gcs_agent.tools}, "
    f"search_agent.tools: {search_agent.tools}"
)

# Required by ADK
root_agent = market_researcher_agent
