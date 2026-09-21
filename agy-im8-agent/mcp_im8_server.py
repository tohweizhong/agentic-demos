import os
import sqlite3
import sys
from mcp.server.fastmcp import FastMCP

# Create the FastMCP server
mcp = FastMCP("IM8PolicyServer")

DB_FILE = os.path.join(os.path.dirname(__file__), "im8_policies.db")

@mcp.tool()
def lookup_im8_policy(rule_id: str) -> str:
    """Look up Singapore Government IM8 policy requirements and severity by rule ID.

    Args:
        rule_id: The IM8 rule identifier (e.g., 'IM8-Sec-01', 'IM8-Data-02', 'IM8-App-04', 'IM8-Infra-03').
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rule_id, clause_title, domain, severity, requirement, remediation_guidance 
            FROM im8_policies 
            WHERE LOWER(rule_id) = LOWER(?)
        """, (rule_id.strip(),))
        row = cursor.fetchone()
        conn.close()

        if row:
            r_id, title, domain, severity, req, guidance = row
            return (
                f"--- IM8 POLICY DEFINITION ---\n"
                f"Rule ID: {r_id}\n"
                f"Clause Title: {title}\n"
                f"Domain: {domain}\n"
                f"Severity: {severity}\n"
                f"Requirement: {req}\n"
                f"Remediation Guidance: {guidance}\n"
            )
        return f"Policy rule '{rule_id}' not found in IM8 policy database."
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

@mcp.tool()
def list_active_im8_policies() -> str:
    """List all active Singapore Government IM8 security policies currently enforced."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT rule_id, clause_title, domain, severity FROM im8_policies ORDER BY rule_id ASC")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No policies found in database."

        output = ["--- ACTIVE IM8 SECURITY POLICIES ---"]
        for r_id, title, domain, severity in rows:
            output.append(f"• [{r_id}] ({severity}) {title} - Domain: {domain}")
        return "\n".join(output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

@mcp.tool()
def get_remediation_pattern(rule_id: str) -> str:
    """Retrieve the official government-approved code remediation template for an IM8 rule.

    Args:
        rule_id: The IM8 rule identifier (e.g., 'IM8-Sec-01', 'IM8-Data-02').
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT file_type, vulnerable_pattern, compliant_replacement, explanation 
            FROM remediation_templates 
            WHERE LOWER(rule_id) = LOWER(?)
        """, (rule_id.strip(),))
        rows = cursor.fetchall()
        conn.close()

        if rows:
            output = [f"--- APPROVED REMEDIATION TEMPLATE FOR {rule_id.upper()} ---"]
            for f_type, vuln, compl, exp in rows:
                output.append(f"Target File Type: {f_type}")
                output.append(f"Explanation: {exp}")
                output.append(f"Vulnerable Pattern:\n{vuln}")
                output.append(f"Compliant Replacement:\n{compl}\n")
            return "\n".join(output)
        return f"No remediation template found for '{rule_id}'."
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
