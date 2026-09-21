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

# Ensure parent directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.tools import (
    audit_code_security,
    audit_infra_security,
    generate_cio_report,
    get_assessment_timestamp,
)

# Shared model config
model_config = Gemini(
    model="gemini-2.5-flash",
    retry_options=types.HttpRetryOptions(attempts=3),
)

# Connect to the FastMCP IM8 Policy Server
mcp_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_im8_server.py"))

im8_policy_mcp_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[mcp_script_path],
        )
    )
)

# --- SPECIALIST 1: CODE SECURITY AUDITOR ---
code_security_agent = Agent(
    name="code_security_specialist",
    model=model_config,
    instruction="""
    You are an autonomous Code Security Specialist for Singapore Government systems.
    Your mission is to audit application source code for:
    - IM8-Sec-01 (No Hardcoded Secrets)
    - IM8-Data-02 (Citizen PII Protection)
    
    Instructions:
    1. Use your MCP tools to check the requirements for IM8-Sec-01 and IM8-Data-02.
    2. Use `audit_code_security` to inspect or remediate target repository files.
    3. If the user requests remediation or auto-fix, pass remediate=True.
    4. Provide clear findings with rule IDs, affected files, and remediation status.
    """,
    output_key="code_audit_result",
    tools=[im8_policy_mcp_tools, audit_code_security]
)

# --- SPECIALIST 2: INFRASTRUCTURE & NETWORK SECURITY AUDITOR ---
infra_security_agent = Agent(
    name="infra_security_specialist",
    model=model_config,
    instruction="""
    You are an autonomous Infrastructure & Network Security Specialist for Singapore Government systems.
    Your mission is to audit infrastructure configurations and API endpoints for:
    - IM8-App-04 (API Debug Route Hardening)
    - IM8-Infra-03 (Cloud Storage Access Hardening)
    
    Instructions:
    1. Use your MCP tools to check the requirements for IM8-App-04 and IM8-Infra-03.
    2. Use `audit_infra_security` to inspect or remediate target repository files.
    3. If the user requests remediation or auto-fix, pass remediate=True.
    4. Provide clear findings with rule IDs, affected files, and remediation status.
    """,
    output_key="infra_audit_result",
    tools=[im8_policy_mcp_tools, audit_infra_security]
)

# --- PIPELINE STEP 1: PARALLEL AUDIT EXECUTION ---
parallel_auditors = ParallelAgent(
    name="parallel_auditors",
    sub_agents=[code_security_agent, infra_security_agent]
)

# --- PIPELINE STEP 2: EXECUTIVE CIO REPORT ASSEMBLER ---
assembler_agent = Agent(
    name="cio_report_assembler",
    model=model_config,
    instruction="""
    You are the Lead Government Compliance Officer and Attestation Specialist.
    Synthesize findings from both audit specialists into an executive CIO attestation report.
    
    Available findings:
    - Code Security Audit: {code_audit_result}
    - Infrastructure Security Audit: {infra_audit_result}
    
    Tasks:
    1. Call `get_assessment_timestamp` to read the real assessment date. Never guess a date.
    2. Determine the overall status. Write COMPLIANT only when every rule reports COMPLIANT or REMEDIATED.
    3. Write NON-COMPLIANT when any rule reports a violation or a failed remediation.
    4. Compile a markdown report with an executive summary, a findings matrix, and an attestation block.
    5. Call `generate_cio_report` to save the report to IM8_COMPLIANCE_REPORT.md.
    6. Return an executive summary of the assessment.
    """,
    output_key="cio_report",
    tools=[generate_cio_report, get_assessment_timestamp]
)

# --- COMPLETE SEQUENTIAL PIPELINE ---
im8_pipeline = SequentialAgent(
    name="im8_pipeline",
    sub_agents=[
        parallel_auditors,
        assembler_agent
    ]
)

root_agent = im8_pipeline

app = App(
    root_agent=root_agent,
    name="app",
)
