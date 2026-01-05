from .travel_desk_agent import TravelDeskAgent
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

root_agent = TravelDeskAgent(
    remote_agent_addresses=[
        os.getenv("FLIGHT_BOOKING_AGENT_URL", "http://localhost:10000"),
        os.getenv("HOTEL_BOOKING_AGENT_URL", "http://localhost:10001"),
    ]
).create_agent()
