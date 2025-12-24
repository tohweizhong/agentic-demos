import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from google.cloud import logging

# Initialize the client
client = logging.Client()

# Create a custom logger for activity tracking
logger = client.logger("cepf-tracking-log-financial-analyst") 

load_dotenv()

def convert_currency(amount:float, from_currency:str, to_currency:str) -> Dict[str, Any]:
    """
    Tool: Currency Converter

    Description:
        Converts a given amount from one currency to another using the Frankfurter API.

    Parameters:
        amount (float): The numeric value to convert.
        from_currency (str): The ISO currency code to convert from (e.g., 'USD').
        to_currency (str): The ISO currency code to convert to (e.g., 'INR').

    Returns:
        dict: {
            "currency": <str>,  # The target currency code
            "amount": <float>,  # The converted amount (or sample fallback if error)
            "error": <str>      # Optional error message if API call fails
        }
    """
    url = f"https://api.frankfurter.app/latest?base={from_currency}&symbols={to_currency}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        rate = data['rates'][to_currency]
        converted_amount = round(amount * rate, 2)
        return {
            "currency": to_currency,
            "amount": converted_amount
        }

    except Exception as e:
        # On failure, return a fallback value and include the error message
        return {
            "currency": to_currency,
            "amount": 123.45,
            "error": str(e)
        }


##############################################################################################################################
# TODO 1: Pass the convert_currency function to the agent as FunctionTool to convert currency using external API.
##############################################################################################################################

currency_converter_tool = FunctionTool(func=convert_currency)

# --- Financial Analyst Agent ---
financial_analyst_agent = Agent(
    name="financial_analyst_agent",
    model="gemini-2.5-pro",
    description="Converts campaign budget from USD to local currency using a currency API.",
    instruction="""
You are a Financial Analyst agent that receives from_currency, to_currency, amount requests and converts them to the local currency of a specified country using `currency_converter_tool`.
eg. Input:
{
  "amount": 10000,
  "from_currency": "USD",
  "to_currency": "JPY"
}

Use the Currency Conversion Tool to convert the amount.

Respond only in following JSON format:
{
  "currency": "local currency for specified country",
  "amount": converted amount in local currency
}
"""

,output_key="financial_analyst_response",
    tools=[currency_converter_tool]
)


# Do not change — used for activity tracking.
logger.log_text(
    f"tools: {financial_analyst_agent.tools}"
)

# --- Required for ADK runtime ---
root_agent = financial_analyst_agent
