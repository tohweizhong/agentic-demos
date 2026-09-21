"""FastMCP server that serves the public IM8 Reform control catalog.

The control data comes from the public Singapore Government ICT&SS Policy
(IM8 Reform) catalog. See init_im8_db.py for the source and the licence.
"""
import os
import sqlite3
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("IM8ControlCatalog")

DB_FILE = os.path.join(os.path.dirname(__file__), "im8_policies.db")


def _query(sql: str, args: tuple):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, args)
        return cursor.fetchall()
    finally:
        conn.close()


@mcp.tool()
def lookup_im8_control(control_id: str) -> str:
    """Look up one control from the public IM8 Reform catalog.

    Args:
        control_id: The control identifier, for example 'as-8', 'lm-19',
            'as-13' or 'ns-2'.

    Returns:
        The title, group, profile level, statement, guidance and source.
    """
    try:
        rows = _query(
            "SELECT control_id, title, control_group, profile_level, statement, "
            "guidance, source FROM im8_controls WHERE LOWER(control_id) = LOWER(?)",
            (control_id.strip(),),
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

    if not rows:
        return f"Control '{control_id}' is not in the local IM8 Reform catalog."

    cid, title, group, level, statement, guidance, source = rows[0]
    return (
        "--- IM8 REFORM CONTROL ---\n"
        f"Control ID: {cid}\n"
        f"Title: {title}\n"
        f"Group: {group}\n"
        f"Profile Level: {level}\n"
        f"Statement: {statement}\n"
        f"Guidance: {guidance}\n"
        f"Source: {source}\n"
    )


@mcp.tool()
def list_im8_controls() -> str:
    """List every control held in the local IM8 Reform catalog."""
    try:
        rows = _query(
            "SELECT control_id, title, control_group, profile_level "
            "FROM im8_controls ORDER BY control_id ASC",
            (),
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

    if not rows:
        return "The local catalog is empty. Run init_im8_db.py first."

    lines = ["--- IM8 REFORM CONTROLS IN SCOPE ---"]
    for cid, title, group, level in rows:
        lines.append(f"[{cid}] {title} - {group} - {level}")
    return "\n".join(lines)


@mcp.tool()
def get_remediation_pattern(control_id: str) -> str:
    """Return the repair template written for one control.

    The templates are teaching examples for this lab. They are not part of
    the published control catalog.

    Args:
        control_id: The control identifier, for example 'as-8'.
    """
    try:
        rows = _query(
            "SELECT file_type, vulnerable_pattern, compliant_replacement, explanation "
            "FROM remediation_templates WHERE LOWER(control_id) = LOWER(?)",
            (control_id.strip(),),
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

    if not rows:
        return f"No repair template exists for '{control_id}'."

    lines = [f"--- REPAIR TEMPLATE FOR {control_id} (lab example) ---"]
    for file_type, vulnerable, compliant, explanation in rows:
        lines.append(f"File Type: {file_type}")
        lines.append(f"Explanation: {explanation}")
        lines.append(f"Vulnerable Pattern:\n{vulnerable}")
        lines.append(f"Compliant Replacement:\n{compliant}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
