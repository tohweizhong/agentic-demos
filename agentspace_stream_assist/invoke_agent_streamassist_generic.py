#!/usr/bin/env python3
"""
Invoke a Gemini Enterprise agent using the v1alpha streamAssist API.

This script demonstrates how to programmatically invoke agents registered in
Gemini Enterprise (Google Cloud Discovery Engine) using the REST API.

Prerequisites:
    - Google Cloud project with Discovery Engine API enabled
    - A Gemini Enterprise search app (engine) created
    - An agent registered in your Gemini Enterprise app
    - Google Cloud credentials configured (gcloud auth application-default login)
    - Required Python packages: google-auth, requests

Installation:
    pip install google-auth requests

Usage:
    1. Update the configuration section below with your project details
    2. Run: python invoke_agent_streamassist_generic.py
"""

import os
import json
import requests
from google.auth.transport.requests import Request
import google.auth


# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES FOR YOUR ENVIRONMENT
# ============================================================================

# Your Google Cloud project ID (found in Cloud Console)
PROJECT_ID = "your-project-id"

# Location where your Discovery Engine is deployed (typically "global" or "us")
LOCATION = "global"

# Collection name (typically "default_collection" unless you created a custom one)
COLLECTION = "default_collection"

# Your Gemini Enterprise app/engine ID
# Find this in Cloud Console > Discovery Engine > Apps
ENGINE_ID = "your-engine-id"

# Assistant ID (typically "default_assistant")
ASSISTANT_ID = "default_assistant"

# Your registered agent's ID
# Find this in your Gemini Enterprise app's agent configuration
AGENT_ID = "your-agent-id"

# Optional: Display name for logging purposes
AGENT_DISPLAY_NAME = "Your Agent Name"

# Sample query to test the agent
SAMPLE_QUERY = "What can you help me with?"

# ============================================================================
# END CONFIGURATION
# ============================================================================


def get_access_token():
    """
    Get OAuth2 access token for Google Cloud API authentication.

    This uses Application Default Credentials (ADC). Ensure you have authenticated via:
        gcloud auth application-default login

    Or set GOOGLE_APPLICATION_CREDENTIALS environment variable to a service account key file.

    Returns:
        str: Valid OAuth2 access token
    """
    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )

    # Refresh token if expired
    if not credentials.valid:
        credentials.refresh(Request())

    return credentials.token


def invoke_agent_streamassist(query: str, verbose: bool = True) -> str:
    """
    Invoke a Gemini Enterprise agent using the v1alpha streamAssist REST API.

    This function sends a query to a specific agent and processes the streaming response.
    The agent must be registered in your Gemini Enterprise app.

    Args:
        query: The text query to send to the agent. Can include @mentions if needed.
        verbose: If True, prints detailed logging information during execution.

    Returns:
        str: The complete response text from the agent, with streaming chunks concatenated.
             Returns empty string if request fails or no response received.

    API Reference:
        https://cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1alpha/projects.locations.collections.engines.assistants/streamAssist
    """

    # Construct the full resource name for the assistant
    # Format: projects/{project}/locations/{location}/collections/{collection}/engines/{engine}/assistants/{assistant}
    assistant_name = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/{COLLECTION}/"
        f"engines/{ENGINE_ID}/assistants/{ASSISTANT_ID}"
    )

    # Construct the v1alpha streamAssist endpoint URL
    url = f"https://discoveryengine.googleapis.com/v1alpha/{assistant_name}:streamAssist"

    if verbose:
        print("=" * 60)
        print("GEMINI ENTERPRISE - AGENT INVOCATION")
        print("=" * 60)
        print(f"Agent: {AGENT_DISPLAY_NAME} (ID: {AGENT_ID})")
        print(f"URL: {url}")
        print(f"Query: {query}")
        print("=" * 60)

    # Get OAuth2 access token for authentication
    token = get_access_token()

    # Prepare HTTP request headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Prepare request body
    # The agentsSpec specifies which registered agent(s) to invoke
    body = {
        "query": {
            "text": query
        },
        "agentsSpec": {
            "agentSpecs": [
                {
                    "agentId": AGENT_ID  # Specify the exact agent to invoke by ID
                }
            ]
        }
    }

    if verbose:
        print("\nRequest body:")
        print(json.dumps(body, indent=2))
        print()

    # Make the HTTP POST request
    if verbose:
        print("Making request...")

    response = requests.post(url, headers=headers, json=body, stream=True)

    if verbose:
        print(f"Response status: {response.status_code}\n")

    # Handle error responses
    if response.status_code != 200:
        error_msg = f"Error {response.status_code}: {response.text}"
        if verbose:
            print("ERROR:")
            print("-" * 60)
            print(error_msg)
            print("-" * 60)
        return ""

    # Process the streaming response
    if verbose:
        print("Response:")
        print("-" * 60)

    full_response = []
    response_text = response.text

    try:
        # Try to parse the response as a complete JSON array
        # The API may return responses in JSON array format
        if response_text.startswith('['):
            data_array = json.loads(response_text)
            for data in data_array:
                # Extract text from each response chunk
                # Response structure: data["answer"]["replies"][n]["groundedContent"]["content"]["text"]
                if "answer" in data and "replies" in data["answer"]:
                    for reply in data["answer"]["replies"]:
                        if "groundedContent" in reply and "content" in reply["groundedContent"]:
                            if "text" in reply["groundedContent"]["content"]:
                                text = reply["groundedContent"]["content"]["text"]
                                # Filter out "thought" text (internal reasoning from agents)
                                # Only include actual response content
                                if not reply["groundedContent"]["content"].get("thought", False):
                                    if verbose:
                                        print(text, end="", flush=True)
                                    full_response.append(text)
    except json.JSONDecodeError:
        # Fallback: parse line by line if array parsing fails
        # Some responses may be newline-delimited JSON objects
        for line in response_text.split('\n'):
            line = line.strip().rstrip(',')
            if line and (line.startswith('{') or line.startswith('[')):
                try:
                    # Remove array brackets if present
                    if line.startswith('['):
                        line = line[1:]
                    if line.endswith(']'):
                        line = line[:-1]
                    line = line.strip().rstrip(',')

                    if line:
                        data = json.loads(line)
                        # Extract text using the same structure as above
                        if "answer" in data and "replies" in data["answer"]:
                            for reply in data["answer"]["replies"]:
                                if "groundedContent" in reply and "content" in reply["groundedContent"]:
                                    if "text" in reply["groundedContent"]["content"]:
                                        text = reply["groundedContent"]["content"]["text"]
                                        # Filter out internal "thought" content
                                        if not reply["groundedContent"]["content"].get("thought", False):
                                            if verbose:
                                                print(text, end="", flush=True)
                                            full_response.append(text)
                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON
                    continue

    if verbose:
        print("\n" + "-" * 60)

    # Return the concatenated response text
    return "".join(full_response)


if __name__ == "__main__":
    """
    Example usage: Test invoking an agent through Gemini Enterprise.

    Before running:
        1. Update the configuration constants at the top of this file
        2. Ensure you have authenticated: gcloud auth application-default login
        3. Verify your agent is properly registered in Gemini Enterprise
    """
    try:
        # Invoke the agent with the sample query
        answer = invoke_agent_streamassist(SAMPLE_QUERY, verbose=True)

        # Print summary
        print(f"\n\nFull answer retrieved: {len(answer)} characters")

        if answer:
            print("\n✓ Successfully invoked agent via streamAssist API!")
        else:
            print("\n✗ No response received from agent")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
