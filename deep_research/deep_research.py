import time
from google import genai

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

# Generate_content works

response = client.models.generate_content(
    model="gemini-2.5-flash", contents="Explain how AI works in a few words"
)
print(response.text)

# interaction =  client.interactions.create(
#     model="gemini-3-flash-preview",
#     input="Tell me a short joke about programming."
# )

# print(interaction.outputs[-1].text)

# interaction = client.interactions.create(
#     input="Research the history of Google TPUs.",
#     agent='deep-research-pro-preview-12-2025',
#     background=True
# )

# print(f"Research started: {interaction.id}")

# while True:
#     interaction = client.interactions.get(interaction.id)
#     if interaction.status == "completed":
#         print(interaction.outputs[-1].text)
#         break
#     elif interaction.status == "failed":
#         print(f"Research failed: {interaction.error}")
#         break
#     time.sleep(10)