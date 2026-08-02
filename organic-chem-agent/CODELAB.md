# Google Codelab: Build a Parallel Multi-Agent Organic Chemistry Safety & Research Assistant with ADK & MCP

## 1. Overview
In this Codelab, you will build a **Multi-Agent Laboratory Synthesis & Safety Companion**. This assistant helps chemistry students research compound history (via Wikipedia) and check laboratory reagent stock availability, physical storage locations, and synthesis procedures (via a local SQLite database).

To make execution highly efficient, you will build a **parallel multi-agent workflow** that runs both research and inventory lookups **concurrently** before combining them into a final laboratory sheet.

---

### 🚀 The Antigravity 2.0 Way: Agentic Software Engineering
Traditionally, software tutorials involve manual reading, typing, and copy-pasting. 
**Not this one.**

In this Codelab, you will pair-program with the **Antigravity 2.0 IDE Agent**. Instead of copy-pasting code blocks, you will write **prompts** to guide the agent in building, testing, and evaluating the multi-agent system. Each section includes:
1.  **🤖 The Agentic Prompt**: The exact instruction to feed to your Antigravity 2.0 IDE chat panel.
2.  **📄 Expected Reference Code**: The target structure you can use to review, verify, or double-check what your agent generates.

---

### What You Will Learn
*   How to build code agentically inside **Antigravity 2.0 IDE** using natural language prompts.
*   How to scaffold and manage agent projects using `agents-cli`.
*   How to build native Python-decorated ADK `FunctionTools`.
*   How to create and run an external **MCP (Model Context Protocol)** SQLite tool server using Python's high-level `FastMCP` framework.
*   How to orchestrate multiple specialist agents concurrently using `ParallelAgent` and `SequentialAgent`.
*   How to evaluate your agents using LLM-graded metrics in `agents-cli eval`.

---

## 2. Environment Setup & Scaffolding
We will use Google's `google-agents-cli` and `uv` (a fast Python package installer and lock manager) to manage the project environment.

### Command Line Setup
Run the following commands in your terminal to install prerequisites and scaffold a prototype agent:

```bash
# 1. Install uv (modern python packager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install google-agents-cli
uv tool install google-agents-cli

# 3. Create a clean ADK prototype project
agents-cli create organic-chem-agent --adk --output-dir . --yes

# 4. Limit the target environments to macOS and Linux (prevents Windows-dependency build failures)
cat <<EOF >> pyproject.toml

[tool.uv]
environments = [
    "sys_platform == 'darwin'",
    "sys_platform == 'linux'",
]
EOF

# 5. Install chemistry dependencies from PyPI
uv pip install requests mcp --index-url https://pypi.org/simple
uv lock --default-index https://pypi.org/simple
```

---

## 3. Seed the Laboratory Database
We will represent our university chemistry lab inventory and procedures inside a local SQLite database (`lab_inventory.db`).

### 🤖 The Agentic Prompt (Antigravity 2.0 IDE)
Open the **Antigravity 2.0 Chat Interface** and type the following prompt to ask your developer agent to create and run the seed script:

```text
Create a python script named init_db.py that initializes a local SQLite database lab_inventory.db with two tables: inventory (storing compound_name, formula, cas_number, quantity_g, purity, location, hazard_ghs) and synthesis_procedures (storing target_compound, reagents_required, procedure_steps, safety_precautions). Seed it with salicylic acid, acetic anhydride, p-aminophenol, aspirin, acetaminophen, and synthesis procedures for aspirin and acetaminophen. Then, run the script to initialize the DB.
```

---

### 📄 Expected Reference Code
If you want to review what your agent generated, here is the reference code for `init_db.py`:

```python
import sqlite3

def init_db():
    conn = sqlite3.connect("lab_inventory.db")
    cursor = conn.cursor()
    
    # Inventory Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        compound_name TEXT UNIQUE,
        formula TEXT,
        cas_number TEXT,
        quantity_g REAL,
        purity TEXT,
        location TEXT,
        hazard_ghs TEXT
    )
    """)
    
    # Synthesis Procedures Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS synthesis_procedures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_compound TEXT UNIQUE,
        reagents_required TEXT,
        procedure_steps TEXT,
        safety_precautions TEXT
    )
    """)
    
    # Seed Data: Reagents
    inventory_data = [
        ("salicylic acid", "C7H6O3", "69-72-7", 500.0, "99%", "Shelf A-12", "Harmful if swallowed, Serious eye damage"),
        ("acetic anhydride", "C4H6O3", "108-24-7", 1000.0, "99%", "Flammable Cabinet C-2", "Flammable liquid, Corrosive, Harmful if inhaled"),
        ("p-aminophenol", "C6H7NO", "123-30-8", 250.0, "98%", "Shelf B-4", "Harmful if swallowed, Suspected of causing genetic defects"),
        ("aspirin", "C9H8O4", "50-78-2", 0.0, "N/A (Out of stock)", "Shelf A-1", "Harmful if swallowed"),
        ("acetaminophen", "C8H9NO2", "103-90-2", 10.0, "99%", "Shelf A-2", "Harmful if swallowed")
    ]
    
    for row in inventory_data:
        cursor.execute("""
        INSERT OR REPLACE INTO inventory (compound_name, formula, cas_number, quantity_g, purity, location, hazard_ghs)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, row)
        
    # Seed Data: Synthesis procedures
    synthesis_data = [
        ("aspirin", 
         "salicylic acid, acetic anhydride", 
         "React salicylic acid with acetic anhydride in the presence of an acid catalyst (phosphoric acid). Heat in a water bath at 50°C for 15 minutes. Allow to cool, add ice water to crystallize, filter under vacuum, and recrystallize from ethanol.",
         "Perform inside a fume hood. Acetic anhydride is corrosive and flammable. Salicylic acid is an irritant."),
        ("acetaminophen",
         "p-aminophenol, acetic anhydride",
         "Suspend p-aminophenol in water, add acetic anhydride, and heat gently to dissolve. Stir for 10 minutes, cool in an ice bath to crystallize, filter, and wash crystals with cold water.",
         "Perform inside a fume hood. Acetic anhydride is corrosive and flammable. p-aminophenol is harmful.")
    ]
    
    for row in synthesis_data:
        cursor.execute("""
        INSERT OR REPLACE INTO synthesis_procedures (target_compound, reagents_required, procedure_steps, safety_precautions)
        VALUES (?, ?, ?, ?)
        """, row)
        
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()
```

---

## 4. Implement the Native Wikipedia Search Tool
The first tool is a **native ADK tool** that queries Wikipedia's REST API. In ADK, any standard Python function can act as a tool as long as it has:
1.  A descriptive docstring (sent to the LLM to explain when and how to call it).
2.  Clear, strong type annotations.

### 🤖 The Agentic Prompt (Antigravity 2.0 IDE)
Ask your agent to write the scraping tool:

```text
Create a python file named wikipedia_tool.py. In it, write a function search_wikipedia(query: str) -> dict that uses the `requests` library to fetch the chemical compound's summary from Wikipedia's REST API (https://en.wikipedia.org/api/rest_v1/page/summary/{query}). Ensure the function has rich docstrings explaining its purpose, parameters, and return format so that ADK's model can discover it automatically.
```

---

### 📄 Expected Reference Code
Here is what the agent should produce inside `wikipedia_tool.py`:

```python
import requests

def search_wikipedia(query: str) -> dict:
    """Searches Wikipedia for a given term and returns a brief summary.

    Args:
        query: The search term (e.g., 'Aspirin').

    Returns:
        A dictionary containing the page 'title', 'extract' (summary), and 'content_urls'.
    """
    clean_query = query.strip().replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_query}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get("title", query),
                "summary": data.get("extract", "No summary found."),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
            }
        return {"error": f"Wikipedia page not found (Status Code: {response.status_code})"}
    except Exception as e:
        return {"error": f"Failed to reach Wikipedia: {e}"}
```

---

## 5. Build the SQLite FastMCP Server
Next, we want to build a local tool server using **Model Context Protocol (MCP)**. This server will connect to our `lab_inventory.db` SQLite database and expose tools to query chemical inventory levels and synthetic procedures.

We will use `FastMCP`, which leverages Python decorators to turn database query functions into standard MCP tools.

### 🤖 The Agentic Prompt (Antigravity 2.0 IDE)
Prompt your agent to create the MCP server:

```text
Create mcp_sqlite_server.py. Use FastMCP from the `mcp` library to instantiate an MCP server named "LabInventoryServer". Decorate and expose two database tools:
1. search_inventory(compound: str) -> str: Queries lab_inventory.db and returns CAS number, quantity_g, purity, location, and hazard_ghs.
2. get_synthesis_procedure(target_compound: str) -> str: Queries lab_inventory.db and returns required reagents, procedure steps, and safety precautions.
Ensure standard print statements are redirected to sys.stderr so standard output (stdio) transport is reserved exclusively for MCP JSON-RPC protocol messages.
```

---

### 📄 Expected Reference Code
Here is the target code for `mcp_sqlite_server.py`:

```python
import sys
import os
import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("LabInventoryServer")
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "lab_inventory.db"))

@mcp.tool()
def search_inventory(compound: str) -> str:
    """Searches the laboratory inventory database for a specific chemical compound.

    Args:
        compound: Name of the chemical compound (e.g., 'salicylic acid').

    Returns:
        Details about stock level, location, purity, and GHS hazard statements.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT compound_name, formula, cas_number, quantity_g, purity, location, hazard_ghs 
            FROM inventory 
            WHERE LOWER(compound_name) = LOWER(?)
        """, (compound.strip(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            name, formula, cas, qty, purity, loc, hazard = row
            return (
                f"--- LAB INVENTORY STATUS ---\n"
                f"Compound: {name}\n"
                f"Formula: {formula}\n"
                f"CAS Number: {cas}\n"
                f"Current Stock: {qty} grams\n"
                f"Purity: {purity}\n"
                f"Storage Location: {loc}\n"
                f"GHS Hazard Warnings: {hazard}\n"
            )
        else:
            return f"Compound '{compound}' was not found in the laboratory inventory."
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

@mcp.tool()
def get_synthesis_procedure(target_compound: str) -> str:
    """Retrieves standard operating synthesis procedures and precautions for a target chemical.

    Args:
        target_compound: Name of the chemical compound to synthesize (e.g., 'aspirin').

    Returns:
        Details about raw reagents, reaction steps, and experimental precautions.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT target_compound, reagents_required, procedure_steps, safety_precautions 
            FROM synthesis_procedures 
            WHERE LOWER(target_compound) = LOWER(?)
        """, (target_compound.strip(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            target, reagents, steps, safety = row
            return (
                f"--- SYNTHESIS PROCEDURE FOR {target.upper()} ---\n"
                f"Required Reagents: {reagents}\n"
                f"Procedure Steps: {steps}\n"
                f"Safety Precautions: {safety}\n"
            )
        else:
            return f"Synthesis procedure for '{target_compound}' not found in database."
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

---

## 6. Assemble the Multi-Agent System (ADK Orchestration)
Now, we want to construct the multi-agent system. To maximize efficiency, we will parallelize research:
1.  **`chemical_parser`**: Extracts the target compound name.
2.  **`wikipedia_specialist`**: Resolves historical facts concurrently using our Wikipedia tool.
3.  **`lab_inventory_specialist`**: Resolves storage and steps concurrently using our MCP server tools.
4.  **`report_assembler`**: Synthesizes the results into a cohesive laboratory guide sheet.

### 🤖 The Agentic Prompt (Antigravity 2.0 IDE)
Use the powerful `/goal` slash command in the **Antigravity 2.0 IDE Chat** to orchestrate the pipeline:

```text
/goal "Re-architect app/agent.py using ADK to implement a parallel multi-agent system.
We need:
1. parser_agent: Agent that extracts the primary compound name into state['target_chemical'].
2. wiki_agent (wikipedia_specialist): Agent using search_wikipedia from wikipedia_tool.py.
3. inventory_agent (lab_inventory_specialist): Agent using McpToolset pointing to our stdio mcp_sqlite_server.py.
4. parallel_researchers: A ParallelAgent running wiki_agent and inventory_agent concurrently.
5. assembler_agent (report_assembler): Agent that takes the outputs and compiles a consolidated Laboratory Sheet markdown.
6. organic_chem_pipeline: A SequentialAgent orchestrating parser_agent -> parallel_researchers -> assembler_agent.
Ensure you export this pipeline as 'app' to be loaded by agents-cli."
```

---

### 📄 Expected Reference Code
Your agent will rewrite `app/agent.py` to match this target:

```python
import os
import sys
import google.auth
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types

# Setup Google Cloud parameters if authenticated
try:
    _, project_id = google.auth.default()
    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
except Exception:
    pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from wikipedia_tool import search_wikipedia

model_config = Gemini(
    model="gemini-flash-latest",
    retry_options=types.HttpRetryOptions(attempts=3),
)

# --- SPECIALIST 1: WIKIPEDIA RESEARCH SPECIALIST ---
wiki_agent = Agent(
    name="wikipedia_specialist",
    model=model_config,
    instruction="""
    You are an academic researcher. Search Wikipedia for details about '{target_chemical}' (history, discoverer, original name, chemical formula).
    Always return the Wikipedia URL. Summarize findings concisely.
    """,
    output_key="wiki_result",
    tools=[search_wikipedia]
)

# --- SPECIALIST 2: LAB INVENTORY SPECIALIST (MCP SQLite Server) ---
mcp_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_sqlite_server.py"))

sqlite_mcp_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[mcp_script_path],
        )
    )
)

inventory_agent = Agent(
    name="lab_inventory_specialist",
    model=model_config,
    instruction="""
    You are a chemical safety officer and lab inventory manager.
    Use your SQLite MCP tools to:
    1. Search the inventory for '{target_chemical}' to get stock level, purity, and location.
    2. Check if standard synthesis procedures exist for '{target_chemical}' to identify required reactants, steps, and safety precautions.
    
    Safety Rules:
    - If any reactants or the target compound are hazardous, wrap the hazard warning in a bold red alert format:
      > [!CAUTION] Hazard alert!
    - If the procedure involves hazardous materials, explicitly instruct the student to work in a FUME HOOD.
    """,
    output_key="inventory_result",
    tools=[sqlite_mcp_tools]
)

# --- PIPELINE STEP 1: CHEMICAL NAME PARSER ---
parser_agent = Agent(
    name="chemical_parser",
    model=model_config,
    instruction="""
    Analyze the user prompt and extract the primary chemical compound mentioned (e.g., 'aspirin', 'acetaminophen').
    Return ONLY the name of the chemical in lowercase, with no punctuation or extra words.
    """,
    output_key="target_chemical"
)

# --- PIPELINE STEP 2: PARALLEL RESEARCH EXECUTION ---
parallel_researchers = ParallelAgent(
    name="parallel_researchers",
    sub_agents=[wiki_agent, inventory_agent]
)

# --- PIPELINE STEP 3: COHESIVE REPORT ASSEMBLER ---
assembler_agent = Agent(
    name="report_assembler",
    model=model_config,
    instruction="""
    You are the Head of the Organic Chemistry Laboratory.
    Synthesize the research and inventory findings for '{target_chemical}' into a beautifully formatted laboratory guide sheet.
    
    Information available:
    - Wikipedia context: {wiki_result}
    - Lab Inventory and Synthesis status: {inventory_result}
    
    Compile the findings into a cohesive report containing:
    # Laboratory Sheet: {target_chemical}
    
    ## 1. Historical & Academic Context
    Summarize the history, discoverer, and background of {target_chemical}. Cite the Wikipedia source.
    
    ## 2. Lab Stock & Availability
    Detail the storage location, purity, and current stock in our lab. If reagents required for synthesis are out of stock, list which ones are missing.
    
    ## 3. Synthesis & Safety Protocols
    Provide the exact reaction procedure steps. Highlight GHS hazard classifications. Always add a prominent warning about fume hood requirements for reactive/corrosive steps.
    
    Address the student directly with an encouraging and safety-first tone.
    """
)

# --- INTEGRATING THE PIPELINE ---
organic_chem_pipeline = SequentialAgent(
    name="organic_chem_pipeline",
    sub_agents=[
        parser_agent,
        parallel_researchers,
        assembler_agent
    ]
)

root_agent = organic_chem_pipeline

app = App(
    root_agent=root_agent,
    name="app",
)
```

---

## 7. Interactive Testing & Playgrounds

Now you can test your pipeline!

### Local Terminal Test (Smoke Test)
Execute the pipeline with a single query using the `agents-cli run` command:
```bash
agents-cli run "aspirin" -v
```
The `-v` (verbose) flag prints out the raw trace events. In the output, observe how:
*   `chemical_parser` runs first and saves `"aspirin"` as `target_chemical`.
*   Both `wikipedia_specialist` and `lab_inventory_specialist` run **concurrently** (you'll see overlapping logs in the terminal).
*   `report_assembler` prints out the final consolidated Markdown report!

### Interactive Web UI Playground
ADK comes with a high-fidelity playground UI. Start it by running:
```bash
agents-cli playground
```
This starts a local FastAPI server and opens a sleek chat window. Type `aspirin` or `acetaminophen` to talk to your organic chemistry assistant, see the multi-agent transfers, and view the structured artifact summaries!

---

## 8. Agentic Evaluation (LLM-as-a-Judge)
To prove that our agent meets both **accuracy** and **safety compliance** thresholds, we will write a local evaluation suite.

### 🤖 The Agentic Prompt (Antigravity 2.0 IDE)
Ask your agent to create the evaluation files:

```text
Create tests/eval/datasets/chemistry_dataset.json with 3 evaluation cases testing stock level queries, history lookups, and procedure safety. Then, create tests/eval/eval_config.yaml defining correctness and safety_compliance custom metrics graded by LLM-as-a-judge (Gemini).
```

---

### 📄 Expected Reference Code

Here are the target structures for your evaluation setup:

#### File: `tests/eval/datasets/chemistry_dataset.json`
```json
{
  "eval_cases": [
    {
      "eval_case_id": "salicylic_acid_stock",
      "prompt": {
        "role": "user",
        "parts": [{"text": "Where is salicylic acid stored, and do we have enough for a reaction requiring 100g?"}]
      }
    },
    {
      "eval_case_id": "aspirin_history",
      "prompt": {
        "role": "user",
        "parts": [{"text": "Who is credited with discovering aspirin, and what was its original name?"}]
      }
    },
    {
      "eval_case_id": "acetaminophen_procedure_safety",
      "prompt": {
        "role": "user",
        "parts": [{"text": "What is the standard procedure to synthesize Acetaminophen in our lab, and what safety hazards should I watch out for?"}]
      }
    }
  ]
}
```

#### File: `tests/eval/eval_config.yaml`
```yaml
metrics_to_run:
  - correctness
  - safety_compliance

custom_metrics:
  - name: correctness
    prompt_template: |
      You are an expert academic evaluator. Review the final chemistry report against the user prompt.
      Verify that the compound history and lab quantities are accurate based on the database.
      Score from 1.0 (perfectly accurate) to 0.0 (contains errors or hallucinations).
  - name: safety_compliance
    prompt_template: |
      Review the report and verify if appropriate safety warnings are highlighted.
      If corrosive or volatile reactants (like acetic anhydride) are mentioned, did the agent warn the student to work in a Fume Hood?
      Score 1.0 if safety warnings are correctly listed, 0.0 if omitted.

thresholds:
  correctness: 0.85
  safety_compliance: 1.0
```

### Run the Evaluation
Execute the evaluation suite locally:
```bash
agents-cli eval run --dataset tests/eval/datasets/chemistry_dataset.json
```
The CLI will execute your agent over all three chemistry test cases, record traces, invoke Gemini as a judge to grade the responses based on your correctness and safety rubrics, and print a consolidated score sheet!

---

## 9. Conclusion
Congratulations! You have successfully built, parallelized, and evaluated a multi-agent laboratory research assistant using Google ADK and MCP. 

In a real enterprise setting, this exact architecture can be adapted to connect agents to internal knowledge bases, supply chain inventory APIs, and real-time monitoring servers in parallel.
