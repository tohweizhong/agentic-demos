import sqlite3
import sys
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("LabInventory")

DB_FILE = "lab_inventory.db"

@mcp.tool()
def search_inventory(compound_name: str) -> str:
    """Search the lab inventory database for stock, storage location, CAS number, and hazard classifications.

    Args:
        compound_name: The name of the chemical compound (e.g., 'salicylic acid', 'acetic anhydride').
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT compound_name, formula, cas_number, quantity_g, purity, location, hazard_ghs 
            FROM inventory 
            WHERE LOWER(compound_name) = LOWER(?)
        """, (compound_name.strip(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            name, formula, cas, qty, purity, loc, hazard = row
            return (
                f"--- LAB INVENTORY SEARCH RESULT ---\n"
                f"Compound: {name.title()}\n"
                f"Formula: {formula}\n"
                f"CAS Number: {cas}\n"
                f"Quantity in Stock: {qty}g\n"
                f"Purity: {purity}\n"
                f"Storage Location: {loc}\n"
                f"GHS Hazards: {hazard}\n"
            )
        else:
            return f"Chemical '{compound_name}' not found in laboratory inventory database."
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return f"Database error: {e}"

@mcp.tool()
def get_synthesis_procedure(target_compound: str) -> str:
    """Look up synthesis procedures and required reagents for a target compound.

    Args:
        target_compound: The compound to synthesize (e.g., 'aspirin', 'acetaminophen').
    """
    try:
        conn = sqlite3.connect(DB_FILE)
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
    # Run the MCP server over stdio
    mcp.run(transport="stdio")
