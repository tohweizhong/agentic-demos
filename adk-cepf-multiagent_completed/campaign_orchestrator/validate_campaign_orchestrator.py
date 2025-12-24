from vertexai import agent_engines

# Replace RESOURCE_ID with your deployed agent resource resource id

resource_id = "RESOURCE_ID"

adk_app = agent_engines.get(resource_id)

# Query the agent
query = "ChronoLeap Smartwatch in Japan and my budget is 200 USD?"
for event in adk_app.stream_query(user_id="your_user_id", message=query):
    print(event)
