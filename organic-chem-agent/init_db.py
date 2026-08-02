import sqlite3

def init_db():
    conn = sqlite3.connect("lab_inventory.db")
    cursor = conn.cursor()
    
    # Create inventory table
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
    
    # Create synthesis table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS synthesis_procedures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_compound TEXT UNIQUE,
        reagents_required TEXT,
        procedure_steps TEXT,
        safety_precautions TEXT
    )
    """)
    
    # Populate inventory
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
        
    # Populate synthesis
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
