"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from a2a.types import AgentCapabilities, AgentSkill, AgentCard
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.apps import A2AStarletteApplication
from a2a.server.tasks import InMemoryTaskStore
from agent import FlightBookingAgent
from agent_executor import FlightBookingAgentExecutor
import uvicorn
from dotenv import load_dotenv
import logging
import os
import click

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default="0.0.0.0")
@click.option("--port", "port", default=10000)
def main(host, port):
    """Entry point for the A2A + LangGraph Flight Booking Agent."""
    try:
        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="create_flight_booking",
            name="Flight Booking Tool",
            description="Helps with booking flights",
            tags=["flight booking creation"],
            examples=["I want to book a flight to Bern."],
        )
        agent_host_url = (
            os.getenv("HOST_OVERRIDE")
            if os.getenv("HOST_OVERRIDE")
            else f"http://{host}:{port}/"
        )
        agent_card = AgentCard(
            name="flight_booking_agent",
            description="Helps with booking flights",
            url=agent_host_url,
            version="1.0.0",
            defaultInputModes=FlightBookingAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=FlightBookingAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        request_handler = DefaultRequestHandler(
            agent_executor=FlightBookingAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)

        logger.info(f"Starting server on {host}:{port}")
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
