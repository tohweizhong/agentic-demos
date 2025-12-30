# main.py
import uvicorn
import os

from shared.server_utils import create_agent_a2a_server  # reuse common A2A function
from agent import creative_director_agent
from a2a.types import AgentSkill

agent = creative_director_agent

def create_creative_director_agent_server(host="localhost"):
    """Create A2A server for Creative Director Agent using the unified wrapper."""
    return create_agent_a2a_server(
        agent=agent,
        name="Creative Director Agent",
        description="Generates a compelling slogan, marketing messages, and a promotional image based on product, demographic, and market context.",
        skills=[
            AgentSkill(
                id="generate_campaign_content",
                name="Generate Campaign Content",
                description="Produce text and image assets (slogan, messages, image) for a new product campaign using demographics and market insights.",
                tags=["campaign", "text", "image", "multimodal", "creative"],
                examples=[
                    "Generate campaign content for ChronoLeap Smartwatch in Japan",
                    "Create slogan and image for smartwatch in India",
                ],
            )
        ],
        host=host,
        status_message="Creating campaign assets...",
        artifact_name="generate_campaign_content"
    )

region = os.environ.get("GOOGLE_CLOUD_LOCATION") 
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
project_number = os.environ.get("PROJECT_NUMBER")

service_url = f"https://creative-director-{project_number}.{region}.run.app"

app = create_creative_director_agent_server(host=service_url)

if __name__ == "__main__":
    uvicorn.run(app.build(), host="0.0.0.0", port=8080)
