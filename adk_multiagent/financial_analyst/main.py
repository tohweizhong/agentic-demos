# main.py
import uvicorn
import os

from shared.server_utils import create_agent_a2a_server  # reuse common A2A function
from agent import financial_analyst_agent
from a2a.types import AgentSkill

agent = financial_analyst_agent

def create_financial_analyst_agent_server(host="localhost"):
    return create_agent_a2a_server(
        agent=agent,
        name="Financial Analyst Agent",
        description="Estimates marketing budget in local currency using product, market, and creative context.",
        skills=[
            AgentSkill(
                id="estimate_budget",
                name="Estimate Campaign Budget",
                description="Provides a cost estimate for the campaign in local currency",
                examples=[
                    "Estimate campaign budget for ChronoLeap Smartwatch in Japan",
                    "How much would it cost to launch SmartRing in India?"
                ],
                tags=["finance", "budget", "currency"]
            )
        ],
        host=host,
        status_message="Calculating localized marketing budget...",
        artifact_name="campaign_budget"
    )

region = os.environ.get("GOOGLE_CLOUD_LOCATION") 
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
project_number = os.environ.get("PROJECT_NUMBER")

service_url = f"https://financial-analyst-{project_number}.{region}.run.app"

app = create_financial_analyst_agent_server(host=service_url)

if __name__ == "__main__":
    uvicorn.run(app.build(), host="0.0.0.0", port=8080)
