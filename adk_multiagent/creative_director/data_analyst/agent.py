from google.adk.agents import Agent
import asyncio
from toolbox_core import ToolboxSyncClient
import os
from google.cloud import logging
from dotenv import load_dotenv

load_dotenv()

# Initialize the client
client = logging.Client()

# Create a custom logger for activity tracking
logger = client.logger("cepf-tracking-log-data-analyst") 


region = os.environ.get("GOOGLE_CLOUD_LOCATION") 
project_number = os.environ.get("PROJECT_NUMBER")

mcp_tool_url = f"https://mcp-bigquery-tool-{project_number}.{region}.run.app"

toolbox = ToolboxSyncClient(mcp_tool_url)

##############################################################################################################################
# TODO 1 : Load toolset named my_bq_toolset you created as part of MCP toolbox.
##############################################################################################################################

tools = toolbox.load_toolset('my_bq_toolset')

###################################################################################################################################
# TODO 2 : Create an agent with "gemini-2.5-pro" model to fetch the demographic data from BigQuery using the tools defined above 
# 2.1 Add model parameter
# 2.2 Add tools parameter
###################################################################################################################################

data_analyst_agent = Agent(
    name="gcp_bigquery_agent",
    model="gemini-2.5-pro",
    description="Agent that fetches demographic data from a BigQuery table.",
    instruction=(
        """
You are an agent that retrieves demographic data strictly from a BigQuery table using the MCP toolset. You must not generate or infer any content yourself.

Step 1:
Extract the country name from the user's query and store it in a variable named user_query_country.

Step 2:
Use this country value to load the BigQuery tool:
    tools = toolbox.load_toolset('my_bq_toolset', bound_params={'country': user_query_country})

Step 3:
Call the appropriate tool from the toolset to retrieve demographic data. Store the result in a variable named demographic_info.

Step 4:
If demographic_info is empty, null, or does not contain valid data, return the following structured JSON response:

{
    "status": "not_found",
    "message": "Demographic data not found for the specified country."
}

Step 5:
Do not create or fabricate any data. If demographic_info is empty or invalid, return an empty JSON object: {}

If demographic_info is valid, format it *exactly* into the following JSON structure using only the values returned from BigQuery:
{
    "age_group": "<Age group value from BigQuery result>",
    "interests": [
        "<Interest 1 from BigQuery result>",
        "<Interest 2 from BigQuery result>",
        "<Interest 3 from BigQuery result>"
    ]
}

Return only the JSON object. Do not include any other explanatory text or content.
        """
    ),
    output_key="demographics",
    tools=tools,
)


# Do not change — used for activity tracking.
logger.log_text(
    f"model: {data_analyst_agent.model}, "
    f"tools: {data_analyst_agent.tools}"
)

root_agent = data_analyst_agent