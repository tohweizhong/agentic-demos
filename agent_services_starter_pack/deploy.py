"""Deploys the sample agent to Agent Runtime, or deletes it.

Usage:
  python deploy.py            Create the agent, or update it if it exists.
  python deploy.py --delete   Delete the agent with its sessions and memories.

The script writes the Agent Runtime name to `.env` as AGENT_RUNTIME_NAME.
The samples read it from there.
"""

import argparse
import os
import sys

import config

# Pinned versions for the agent on Agent Runtime are in agent/requirements.txt.
REQUIREMENTS_FILE = config.PACK_DIR / "agent" / "requirements.txt"


def requirements():
  """Returns the package lines in agent/requirements.txt."""
  lines = REQUIREMENTS_FILE.read_text().splitlines()
  return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def env_vars(settings):
  """Environment variables for the agent on Agent Runtime."""
  values = {
      "MODEL": settings.model,
      # Turns on the built-in ADK traces, logs, and metrics.
      "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
      # Uses the latest generative AI semantic conventions in the traces.
      "OTEL_SEMCONV_STABILITY_OPT_IN": "gen_ai_latest_experimental",
  }
  if settings.capture_message_content:
    # Logs prompts, responses, and user IDs. Get user consent first.
    values["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "EVENT_ONLY"
  return values


def context_spec(settings):
  """Memory Bank config for the Agent Runtime instance."""
  return {
      "memory_bank_config": {
          # Memory generation. gemini-3.5-flash has ML processing in Singapore.
          "generation_config": {"model": settings.generation_model_resource},
          # Similarity search. No Google embedding model has ML processing in
          # Singapore. You can change this model only before the first memory
          # is stored.
          "similarity_search_config": {
              "embedding_model": settings.embedding_model_resource
          },
      }
  }


def runtime_config(settings):
  """The full deploy config."""
  return {
      "display_name": settings.agent_display_name,
      "description": "Agent services starter pack: Sessions, Memory Bank, traces.",
      "staging_bucket": settings.staging_bucket_uri,
      "requirements": requirements(),
      # Uploads the agent/ folder, so that Agent Runtime can import it.
      "extra_packages": ["agent"],
      "env_vars": env_vars(settings),
      "context_spec": context_spec(settings),
      "labels": {"starter-pack": "agent-services"},
  }


def deploy(settings):
  import agentplatform  # pylint: disable=import-outside-toplevel
  from agentplatform.frameworks import AdkApp  # pylint: disable=import-outside-toplevel

  # extra_packages uses paths relative to the pack folder.
  os.chdir(config.PACK_DIR)
  # The agent reads MODEL when it is imported. Set it before the import.
  os.environ["MODEL"] = settings.model
  from agent.agent import root_agent  # pylint: disable=import-outside-toplevel

  client = agentplatform.Client(project=settings.project_id, location=settings.region)
  app = AdkApp(agent=root_agent)
  cfg = runtime_config(settings)

  print(f"Project:          {settings.project_id}")
  print(f"Region:           {settings.region}")
  print(f"Model:            {settings.model}")
  print(f"Memory model:     {settings.generation_model_resource}")
  print(f"Embedding model:  {settings.embedding_model_resource}")
  print("Deploy takes some minutes.")

  if settings.agent_runtime_name:
    print(f"Updating {settings.agent_runtime_name}")
    runtime = client.runtimes.update(
        name=settings.agent_runtime_name, agent=app, config=cfg
    )
  else:
    print("Creating a new Agent Runtime instance")
    runtime = client.runtimes.create(agent=app, config=cfg)

  name = runtime.api_resource.name
  config.set_env_value(config.ENV_FILE, "AGENT_RUNTIME_NAME", name)
  print(f"\nDone. AGENT_RUNTIME_NAME={name}")
  print("The name is saved in .env. Run the samples in samples/ next.")


def delete(settings):
  import agentplatform  # pylint: disable=import-outside-toplevel

  name = settings.require_runtime_name()
  client = agentplatform.Client(project=settings.project_id, location=settings.region)
  print(f"Deleting {name} with its sessions and memories.")
  # force=True also deletes the child resources (sessions and memories).
  client.runtimes.delete(name=name, force=True)
  config.set_env_value(config.ENV_FILE, "AGENT_RUNTIME_NAME", "")
  print("Deleted. AGENT_RUNTIME_NAME is cleared in .env.")


def main(argv=None):
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument("--delete", action="store_true", help="Delete the agent.")
  args = parser.parse_args(argv)
  try:
    settings = config.load_settings()
  except config.SettingsError as error:
    sys.exit(f"ERROR: {error}")
  if args.delete:
    delete(settings)
  else:
    deploy(settings)


if __name__ == "__main__":
  main()
