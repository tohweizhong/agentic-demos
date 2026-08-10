# ADK 2.0 Examples

This directory contains three examples demonstrating key concepts in the **Google Agent Development Kit (ADK) 2.0**:

1.  **Routing (Graph Workflow):** [`demo1_routing/agent.py`](file:///usr/local/google/home/weizhongt/coding/agentic-demos/adk2_examples/demo1_routing/agent.py) - Shows how to build a deterministic graph with conditional routing using `Workflow` and `Event(route=...)`.
    *   **How to Demo:** Send `"I need to report a bug and check my shipping status."`. The agent will classify this into multiple categories ("BUG" and "LOGISTICS") and trigger both handlers in parallel.
2.  **Human-in-the-Loop (HITL):** [`demo2_hitl/agent.py`](file:///usr/local/google/home/weizhongt/coding/agentic-demos/adk2_examples/demo2_hitl/agent.py) - Demonstrates how to pause a workflow for user input using `RequestInput` and resume it.
    *   **How to Demo:** 
        1. Send `"start"`. 
        2. The agent will suspend and prompt you: `"Enter a number:"`.
        3. Enter a number (e.g., `"5"`) in the chat.
        4. The agent will resume and output the result (`10`).
3.  **Dynamic Loop:** [`demo3_dynamic_loop/agent.py`](file:///usr/local/google/home/weizhongt/coding/agentic-demos/adk2_examples/demo3_dynamic_loop/agent.py) - Illustrates how to implement iterative logic (like a code-and-fix loop) using standard Python control flow with `@node` and `Context.run_node`.
    *   **How to Demo:** Send `"Write a script to say hello"`. The workflow will run the coder agent, detect a mocked lint finding ("Missing comments explaining the code"), yield an intermediate event updating you on the error, call the fixer agent to fix it, and finally return the verified code.



## Setup

1.  Ensure you have active credentials and a Google Cloud project set up:
    ```bash
    gcloud auth application-default login
    ```
2.  Activate the Python virtual environment:
    ```bash
    source .venv/bin/activate
    ```
3.  Set the environment variable to use Vertex AI (if applicable):
    ```bash
    export GOOGLE_GENAI_USE_VERTEXAI=1
    ```

## Running the Examples

You can run these examples in three ways:

### 1. Programmatically (Direct Python Execution)
Each agent folder contains a self-contained script that can be run directly. This is useful for quick CLI testing.

```bash
# Run Routing Demo
python demo1_routing/agent.py

# Run HITL Demo
python demo2_hitl/agent.py

# Run Dynamic Loop Demo
python demo3_dynamic_loop/agent.py
```

### 2. Via ADK CLI (`adk run`)
You can use the ADK CLI to run an agent interactively in the terminal.

```bash
# Run the Routing Demo interactively
adk run demo1_routing

# Run with a query
adk run demo1_routing "I need to report a bug"
```

### 3. Via ADK Web (Local Web UI Playground)
This is the recommended way to interact with the agents, especially for HITL and complex workflows.

To start the Web UI for **all** agents in this directory:
```bash
adk web .
```
Open your browser and navigate to `http://127.0.0.1:8000`. You will see a list of the three agents and can interact with them in a chat interface.

To run only a single agent:
```bash
adk web demo1_routing
```
