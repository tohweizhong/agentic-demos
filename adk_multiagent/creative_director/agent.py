import uuid
import os
import sys
from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool, FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.sequential_agent import SequentialAgent

try:
    # Absolute imports — work in Cloud Run
    from data_analyst.agent import data_analyst_agent
    from market_researcher.agent import market_researcher_agent
except ImportError:
    # Relative imports — work locally with `adk web`
    from .data_analyst.agent import data_analyst_agent
    from .market_researcher.agent import market_researcher_agent

from google import genai
from google.cloud import storage
from google.cloud import logging

# Initialize the client
client = logging.Client()

# Create a custom logger for activity tracking
logger = client.logger("cepf-tracking-log-creative-director") 


# Load credentials
load_dotenv()

project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
location = os.environ['GOOGLE_CLOUD_LOCATION']
bucket_name = os.environ["GOOGLE_CLOUD_PROJECT"] 

# Initialize GenAI client (Vertex AI)
genai_client = genai.Client(vertexai=True, project=project_id, location=location)

# Initialize GCS client
gcs_client = storage.Client()
bucket = gcs_client.bucket(bucket_name)


# --- Image Generation Tool ---
def generate_image(prompt: str, tool_context: ToolContext) -> dict:
    image_response = genai_client.models.generate_images(
        model=os.getenv("IMAGE_MODEL", "imagen-4.0-generate-preview-06-06"),
        prompt=prompt,
    )

    # Extract image bytes
    image_bytes = image_response.generated_images[0].image.image_bytes

    # Generate unique filename
    filename = f"creative_image_{uuid.uuid4().hex}.png"
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/png")

    image_uri = f"gs://{bucket_name}/{filename}"
    return {"image_uri": image_uri}

image_generation_tool = FunctionTool(func=generate_image)

# --- Aggregator Agent to combine responses and generate promotional image for campaign  ---
aggregator_agent = LlmAgent(
    name="combine_data_and_market_response",
    model="gemini-2.5-pro",
    description="Creates campaign slogan, messages, and an image from demographics and market context.",
    instruction="""
You are a Creative Director working on a marketing campaign for a new product.
You do NOT generate any content yourself.

Use the following tools:
- image_generation_tool: Generates a promotional image and stores it in GCS.

Extract country and product from user query.

Input:
{
  "product": "",
  "country": ""
}

Steps:

1. Based on product, {demographics}, and {market_context}, generate:
   - a compelling campaign_slogan
   - 3 short localized key_messages
   - a vivid image_prompt describing the promotional image
2. You must use image_generation_tool to generate promotional image and get `image_uri`. Image generation is not optional and every response must have promotional image.
3. Return ONLY the following information in JSON format. Do not provide output from previous agents.:
{
  "product_name": "<product>",
  "target_country": "<country>",
  "campaign_slogan": "...",
  "target_demographic": {
    "age_group": "...",
    "interests": ["...", "..."]
  },
  "key_messages": ["...", "...", "..."],
  "image_url": "gs://..."
}
"""
,output_key="combine_data_and_market_response",
tools=[image_generation_tool]
)

##############################################################################################################################
# TODO 1: Create a sequential agent and pass following agents as sub agents in sequence:
# 1. data_analyst_agent
# 2. market_researcher_agent
# 3. aggregator_agent - combines response from data_analyst_agent and market_researcher_agent and generates promotion image
##############################################################################################################################

creative_director_agent = SequentialAgent(
    name="creative_director_agent",
    sub_agents=[data_analyst_agent,market_researcher_agent,aggregator_agent],        
    description="Pipeline agent that generates a full marketing campaign using data analysis, market researcher, and aggregator."
   
)

# Do not change — used for activity tracking.
logger.log_text(
    f"sub_agents: {creative_director_agent.sub_agents}"
)

# Required by ADK runtime
root_agent = creative_director_agent
