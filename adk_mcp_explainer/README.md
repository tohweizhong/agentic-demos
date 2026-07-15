# ADK Agent and Secure MCP Server on Cloud Run

This repository contains the code and configuration for building a secure MCP server and an ADK Agent deployed to Google Cloud Run, based on the following Google Developer Codelabs:

## Reference Codelabs

1.  **[How to deploy a secure MCP server on Cloud Run](https://codelabs.developers.google.com/codelabs/cloud-run/how-to-deploy-a-secure-mcp-server-on-cloud-run)**
    *   Located in the `mcp-on-cloudrun/` subdirectory.
    *   Implements a Zoo Animal MCP Server using FastMCP with tools (`get_animals_by_species`, `get_animal_details`) and prompts (`find`).
    *   Includes a `Dockerfile` for containerized deployment on Cloud Run.

2.  **[Build and deploy an ADK agent that uses an MCP server on Cloud Run](https://codelabs.developers.google.com/codelabs/cloud-run/use-mcp-server-on-cloud-run-with-an-adk-agent)**
    *   Located at the root of this workspace.
    *   Implements a Zoo Tour Guide AI Agent using the Agent Development Kit (ADK) that orchestrates a Sequential workflow (Greeter -> Researcher -> Formatter) using the secure MCP server and Wikipedia.
