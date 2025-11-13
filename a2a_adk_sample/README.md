i# User Guide: Deploying an A2A Agent to Cloud Run and Registering with Agentspace

This guide provides a comprehensive walkthrough of deploying an A2A (Agent-to-Agent) enabled agent, built with the Google Agent Development Kit (ADK), to Google Cloud Run. You will also learn how to register your deployed agent with Agentspace to make it discoverable and usable by other agents.

## Introduction

This project provides a template for creating and deploying a powerful, Gemini-based agent that can communicate with other agents using the A2A protocol. By the end of this guide, you will have a publicly accessible agent running on Cloud Run, ready to be integrated into the A2A ecosystem.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

*   **Google Cloud SDK:** [Install the gcloud CLI](https://cloud.google.com/sdk/docs/install).
*   **A Google Cloud Project:** You will need a project with billing enabled to deploy to Cloud Run.
*   **Authentication:** Log in to your Google Cloud account and set up application default credentials:
    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```

## Project Structure

The `to_deploy` directory contains all the necessary files for deploying the agent:

*   `main.py`: The main entry point for the application. It initializes and runs the FastAPI web server.
*   `gemini_agent.py`: Contains the core logic and definition of the Gemini agent, including its system instructions and tools.
*   `agent_executor.py`: Handles the execution of agent tasks by interfacing with the Google Agent Development Kit (ADK).
*   `requirements.txt`: A list of all the Python dependencies required for the agent to run.
*   `Procfile`: Specifies the command to start the web server, used by Google Cloud Run during deployment.
*   `deploy.sh`: A shell script that automates the entire deployment process.

## The ADK Agent (`gemini_agent.py`)

The heart of our application is the `GeminiAgent` class in `gemini_agent.py`. This class inherits from the `LlmAgent` provided by the Google ADK, and it's where you define your agent's identity, capabilities, and tools.

### Agent Identity

The agent's identity is defined by its `name` and `description`. You can customize these to reflect your agent's purpose:

```python
class GeminiAgent(LlmAgent):
    """An agent powered by the Gemini model via Vertex AI."""

    # --- AGENT IDENTITY ---
    name: str = "gemini_agent"
    description: str = "A helpful assistant powered by Gemini."
```

### System Instructions

The `instructions` variable within the `__init__` method sets the agent's system prompt. This is where you can define the agent's personality, its role, and any constraints on its behavior.

```python
class GeminiAgent(LlmAgent):
    def __init__(self, **kwargs):
        # --- SET YOUR SYSTEM INSTRUCTIONS HERE ---
        instructions = """
        You are a helpful and friendly assistant. Your task is to answer user queries using puns, if a city is mentioned, answer in the language spoken there.

        You can use the weather tool to find the weather in a location.
        """
```

### Tools

The ADK allows you to extend your agent's capabilities by giving it tools. In this example, we have a `get_weather` function that the agent can call. You can add your own tools by defining a Python function and registering it in the `tools` list.

```python
# --- DEFINE YOUR TOOLS HERE ---
def get_weather(location: str) -> str:
    """Gets the weather for a given location."""
    # In a real scenario, you might call a weather API here.
    return f"The weather in {location} is sunny."

class GeminiAgent(LlmAgent):
    def __init__(self, **kwargs):
        # --- REGISTER YOUR TOOLS HERE ---
        tools = [
            get_weather
        ]
```

## The A2A Executor (`agent_executor.py`)

The `AdkAgentToA2AExecutor` class in `agent_executor.py` is the bridge between the A2A framework and your ADK agent. It implements the `AgentExecutor` interface from the A2A library and is responsible for handling incoming requests and invoking your agent.

The `execute` method is the core of this class. It performs the following steps:

1.  **Retrieves the user's query** from the `RequestContext`.
2.  **Manages the task lifecycle**, creating a new task if one doesn't exist.
3.  **Manages the session**, creating a new session if one doesn't exist.
4.  **Invokes the ADK Runner** by calling `self._runner.run_async()`, passing the user's query.
5.  **Streams the response** back to the A2A framework, updating the task with the final result.

This executor ensures that your ADK-based agent can seamlessly communicate within the A2A protocol.

## Deployment

The `deploy.sh` script automates the deployment process. To deploy your agent, navigate to the `to_deploy` directory and run the script with your Google Cloud Project ID and a name for your new service. You can also optionally specify the Gemini model to use.

```bash
bash deploy.sh <YOUR_PROJECT_ID> <YOUR_SERVICE_NAME> [MODEL_NAME]
```

*   `MODEL_NAME`: Optional. Can be `gemini-2.5-pro` or `gemini-2.5-flash`. Defaults to `gemini-2.5-flash` if not specified.

For example:

```bash
# Deploy with the default gemini-2.5-flash model
bash deploy.sh my-gcp-project my-gemini-agent

# Deploy with the gemini-2.5-pro model
bash deploy.sh my-gcp-project my-gemini-agent gemini-2.5-pro
```

The script will:

1.  **Build a container image** from your source code.
2.  **Push the image** to the Google Container Registry.
3.  **Deploy the image** to Cloud Run.
4.  **Set environment variables**, including the `MODEL` and the public `AGENT_URL` of the service itself.

Once the script completes, it will print the public URL of your deployed agent.

## Registration with Agentspace

Now that your agent is deployed, you need to register it with Agentspace to make it discoverable. This is done programmatically using the Discovery Engine API.

**1. Get your Agentspace Engine ID:**

You can find your Engine ID in the Google Cloud Console.

**2. Register the agent:**

Execute the following `curl` command, replacing the placeholders with your own values:

```bash
curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" https://discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/collections/default_collection/engines/ENGINE_ID/assistants/default_assistant/agents -d '{
  "name": "AGENT_NAME",
  "displayName": "AGENT_DISPLAY_NAME",
  "description": "AGENT_DESCRIPTION",
  "a2aAgentDefinition": {
     "jsonAgentCard": "{\"provider\": {\"url\": \"AGENT_URL\"},\"name\": \"AGENT_NAME\",\"description\": \"AGENT_DESCRIPTION\",  \"authentication\": { \"schemes\": \"CREDENTIAL_KEY\", \"credentials\": \"CREDENTIAL_VALUE\" }}"
  }
}'
```

**Placeholder Descriptions:**

*   `PROJECT_NUMBER`: Your Google Cloud project number.
*   `LOCATION`: The location of your Discovery Engine instance (e.g., `global`).
*   `ENGINE_ID`: The ID of your Agentspace engine.
*   `AGENT_NAME`: A unique name for your agent.
*   `AGENT_DISPLAY_NAME`: The name that will be displayed in the Agentspace UI.
*   `AGENT_DESCRIPTION`: A brief description of your agent's capabilities.
*   `AGENT_URL`: The public URL of your deployed agent.
*   `CREDENTIAL_KEY`: The key for your authentication credentials (e.g., `Authorization`).
*   `CREDENTIAL_VALUE`: The value for your authentication credentials (e.g., `Bearer <YOUR_TOKEN>`).

**Note on Credentials:** At execution time, when Agentspace talks to the agent, the HTTP authorization header will be set to `"CREDENTIAL_KEY: CREDENTIAL_VALUE"`.

**3. Locate the agent on the Agentspace UI:**

Your agent can be found in the Agentspace UI. Once you click it, you can interact with the agent.

### IAM Support for Agents Running on Cloud Run

When the agent is deployed on Cloud Run (when the `AGENT_URL` ends with "run.app"), Agentspace attempts IAM authentication when talking to the agent. For this to work, you should grant the "Cloud Run Invoker" role to the following principal in the project where Cloud Run is running:

`service-PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com`

### Unregistering the Agent (Optional)

The following command can be used to unregister the agent:

```bash
curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" https://discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/collections/default_collection/engines/ENGINE_ID/assistants/default_assistant/agents/AGENT_ID
```


## Conclusion

Congratulations! You have successfully deployed an A2A-enabled agent to Cloud Run and registered it with Agentspace. Your agent is now ready to interact with other agents in the A2A ecosystem. You can further customize your agent by adding more tools, refining its system instructions, and enhancing its capabilities.
