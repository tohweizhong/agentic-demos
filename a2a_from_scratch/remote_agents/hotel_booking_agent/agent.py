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

from pydantic import BaseModel
import uuid
from crewai import Agent, Crew, LLM, Task, Process
from crewai.tools import tool
from dotenv import load_dotenv
import litellm
import os

load_dotenv()

litellm.vertex_project = os.getenv("GOOGLE_CLOUD_PROJECT")
litellm.vertex_location = os.getenv("GOOGLE_CLOUD_LOCATION")


# class OrderItem(BaseModel):
#     name: str
#     quantity: int
#     price: int

class HotelToBeBooked(BaseModel):
    hotel_name: str

# class Order(BaseModel):
#     order_id: str
#     status: str
#     order_items: list[OrderItem]

class HotelBooking(BaseModel):
    hotel_name: str
    booking_id: str
    status: str

@tool("create_hotel_booking")
def create_hotel_booking(hotel_to_be_booked: str) -> str:
    """
    Creates a new hotel booking with the given hotel.

    Args:
        hotel_to_be_booked: Hotel to be booked.

    Returns:
        str: A message indicating that the booking is completed..
    """
    try:
        booking_id = str(uuid.uuid4())
        hotel_booking = HotelBooking(hotel_name=hotel_to_be_booked, booking_id=booking_id, status="booked")
        print("===")
        print(f"Booking created: {hotel_booking}")
        print("===")
    except Exception as e:
        print(f"Error creating order: {e}")
        return f"Error creating order: {e}"
    return f"Booking {hotel_booking.model_dump()} has been created"


class HotelBookingAgent:
    TaskInstruction = """
# INSTRUCTIONS

You are a specialized assistant for hotel booking.
Your sole purpose is to answer questions about which hotels are available for booking, their location, and their price tier. These information will allow you to handle the hotel booking operation.
If the user asks about anything other than hotel availability or hotel booking, politely state that you cannot help with that topic and can only assist with hotel availability and hotel booking.
Do not attempt to answer unrelated questions or use tools for other purposes.

# CONTEXT

Received user query: {user_prompt}
Session ID: {session_id}

Provided below are the available hotels and their respective locations and price_tiers
- Hilton Basel: Basel, Luxury
- Marriott Zurich: Zurich, Upscale
- Hyatt Regency Basel: Basel, Upper Upscale
- Radisson Blu Lucerne: Lucerne, Midscale
- Best Western Bern: Bern, Upper Midscale
- InterContinental Geneva: Geneva, Luxury
- Sheraton Zurich: Zurich, Upper Upscale
- Holiday Inn Basel: Basel, Upper Midscale
- Courtyard Zurich: Zurich, Upscale
- Comfort Inn Bern: Bern, Midscale

# RULES

- If user want to do something, you will be following this order:
    1. Always ensure the user already confirmed the hotel and the price tier. This confirmation may already given in the user query.
    2. Use `create_hotel_booking` tool to book the hotel
    3. Finally, always provide response to the user about the detailed booking, and their booking ID
    
- Set response status to input_required if asking for user booking confirmation.
- Set response status to error if there is an error while processing the request.
- Set response status to completed if the request is complete.
- DO NOT make up any information, including hotels and price tiers. Always rely on the provided information given to you as context.
"""
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def invoke(self, query, sessionId) -> str:
        model = LLM(
            model="vertex_ai/gemini-2.5-flash-lite",  # Use base model name without provider prefix
        )
        hotel_booking_agent = Agent(
            role="Hotel Booking Agent",
            goal=(
                "Help user to understand what hotels are available for booking, their location, and their price tier."
            ),
            backstory=("You are an expert and helpful hotel booking agent."),
            verbose=False,
            allow_delegation=False,
            tools=[create_hotel_booking],
            llm=model,
        )

        agent_task = Task(
            description=self.TaskInstruction,
            agent=hotel_booking_agent,
            expected_output="Response to the user in friendly and helpful manner",
        )

        crew = Crew(
            tasks=[agent_task],
            agents=[hotel_booking_agent],
            verbose=False,
            process=Process.sequential,
        )

        inputs = {"user_prompt": query, "session_id": sessionId}
        response = crew.kickoff(inputs)
        return response


if __name__ == "__main__":
    agent = HotelBookingAgent()
    result = agent.invoke("I would like to book Hilton Basel please", "default_session")
    print(result)
