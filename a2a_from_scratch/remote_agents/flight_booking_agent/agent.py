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

from langchain_google_vertexai import ChatVertexAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

memory = MemorySaver()


# class OrderItem(BaseModel):
#     name: str
#     quantity: int
#     price: int


# class Order(BaseModel):
#     order_id: str
#     status: str
#     order_items: list[OrderItem]


class FlightToBeBooked(BaseModel):
    destination: str

# class Order(BaseModel):
#     order_id: str
#     status: str
#     order_items: list[OrderItem]

class FlightBooking(BaseModel):
    destination: str
    booking_id: str
    status: str


@tool
def create_flight_booking(flight_to_be_booked: str) -> str:
    """
    Creates a new flight booking with the given travel destination (Switzerland city).

    Args:
        flight_to_be_booked: Flight to be booked.

    Returns:
        str: A message indicating that the booking has been created.
    """
    try:
        booking_id = str(uuid.uuid4())
        flight_booking = FlightBooking(destination=flight_to_be_booked, booking_id=booking_id, status="booked")
        print("===")
        print(f"Booking created: {flight_booking}")
        print("===")
    except Exception as e:
        print(f"Error creating order: {e}")
        return f"Error creating order: {e}"
    return f"Booking {flight_booking.model_dump()} has been created"


class FlightBookingAgent:
    SYSTEM_INSTRUCTION = """
# INSTRUCTIONS

You are a specialized assistant for flight booking.
Your sole purpose is to answer questions about what flights are are available, and also handle the booking of flights.
If the user asks about anything other than available flights or booking of flights, politely state that you cannot help with that topic and can only assist with availability of flights and booking of flights.
Do not attempt to answer unrelated questions or use tools for other purposes.

# CONTEXT

Provided below are the available flights and their related fares. All flights fly from Singapore to Switzerland, and are return only, i.e. no one-way flights:
- To Basel: SGD2,000
- To Zurich: SGD2,100
- To Lucerne: SGD2,200
- To Bern: SGD2,300
- To Geneva: SGD2,400

# RULES

- If user want to do something, you will be following this order:
    1. Always ensure the user already confirmed the flight that they want and the fare. This confirmation may already given in the user query.
    2. Use `create_flight_booking` tool to create the booking
    3. Finally, always provide response to the user about the detailed booking, total fare, and booking ID.

- DO NOT make up any flights or fare, Always rely on the provided options given to you as context.
"""
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.model = ChatVertexAI(
            model="gemini-2.5-flash-lite",
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        )
        self.tools = [create_flight_booking]
        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
        )

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        self.graph.invoke({"messages": [("user", query)]}, config)
        return self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        return current_state.values["messages"][-1].content
