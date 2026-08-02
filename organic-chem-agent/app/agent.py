import os
import sys
import google.auth
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
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

# Ensure parent directory is in Python path so we can import wikipedia_tool
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from wikipedia_tool import search_wikipedia

# Define shared model configuration
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
# Runs Wikipedia and Lab Inventory lookups concurrently!
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
# Ties all steps together sequentially: Parse -> Run Parallel Researchers -> Assemble Final Report
organic_chem_pipeline = SequentialAgent(
    name="organic_chem_pipeline",
    sub_agents=[
        parser_agent,
        parallel_researchers,
        assembler_agent
    ]
)

# Export the root agent and register it in the ADK App
root_agent = organic_chem_pipeline

app = App(
    root_agent=root_agent,
    name="app",
)
