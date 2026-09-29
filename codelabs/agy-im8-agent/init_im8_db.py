"""Seed the local IM8 control database.

The control identifiers, statements and guidance come from the public
Singapore Government ICT&SS Policy (IM8 Reform) control catalog.

    Source:  https://github.com/GovTechSG/tech-standards
    File:    catalogs/im8-reform.json
    Version: 2025.05.13
    Licence: MIT, Government Technology Agency of Singapore

The full Instruction Manual 8 is not public. Only the IM8 Reform control
catalog for low-risk cloud systems is published. This lab uses four controls
from that public catalog.
"""
import sqlite3

DB_FILE = "im8_policies.db"

CATALOG_SOURCE = "GovTechSG/tech-standards catalogs/im8-reform.json v2025.05.13"

# Four controls from the public IM8 Reform catalog.
# profile_level records the low-risk cloud profile that carries the control.
#   Level 0 = must-have, Level 1 = should-have, Level 2 = good-to-have.
CONTROLS = [
    (
        "as-8",
        "Secrets Management",
        "Application Security",
        "Level 1 (Should-Have)",
        "Securely store secrets in an appropriate secrets management solution "
        "with access control enforcement, encryption, and monitoring.",
        "Secrets include API keys, access keys, and other static credentials. "
        "Do not store secrets unencrypted in source code or configuration files. "
        "Store secrets in cloud-native solutions like Google Cloud Secret Manager, "
        "or cloud-agnostic solutions like HashiCorp Vault.",
        CATALOG_SOURCE,
    ),
    (
        "lm-19",
        "Log Sanitisation",
        "Logging and Monitoring",
        "Level 2 (Good-to-Have)",
        "Sanitise logs to protect classified and sensitive data before it is "
        "recorded in any logging system or shared to any third party.",
        "Identify types of classified and sensitive data that may appear in logs. "
        "When logging, consider using sanitisation techniques like masking or "
        "tokenisation. This ensures that sensitive information, such as personal "
        "data, credentials, API keys, and payment details, are not stored in "
        "plaintext during log collection.",
        CATALOG_SOURCE,
    ),
    (
        "as-13",
        "Exposure of Internal System Details",
        "Application Security",
        "Level 2 (Good-to-Have)",
        "Prevent the unnecessary disclosure of internal system details to end users.",
        "Ensure all system messages and notifications are informative yet secure. "
        "These messages should be contextually appropriate, providing end-users with "
        "relevant information without exposing internal system details such as debug "
        "information, stack traces, or software versioning.",
        CATALOG_SOURCE,
    ),
    (
        "ns-2",
        "Access Restrictions on CSP Resources Outside Virtual Network",
        "Network Security",
        "Level 1 (Should-Have)",
        "Restrict access to CSP resources outside of a virtual network using access "
        "controls or application layer authorisation.",
        "Apply access restrictions appropriate to the resource type. Restrict access "
        "to object storage buckets with IAM policies and block public access from "
        "the internet.",
        CATALOG_SOURCE,
    ),
]

# Repair templates written for this lab. These are teaching examples.
# They are not part of the published control catalog.
TEMPLATES = [
    (
        "as-8",
        "yaml",
        'apex_service_key: "apex-sec-prod-9841294812"',
        'apex_service_key: "${APEX_SERVICE_KEY}"',
        "Replace the static service key with an environment variable placeholder.",
    ),
    (
        "lm-19",
        "python",
        "logger.info(f\"... NRIC: {application.nric} ... Phone: {application.phone_number}\")",
        "masked_nric = application.nric[:1] + 'XXXX' + application.nric[-4:]\n"
        "masked_phone = 'XXXX-' + application.phone_number[-4:]",
        "Mask the national identity number and the telephone number before logging.",
    ),
    (
        "as-13",
        "python",
        '@app.get("/api/v1/debug/dump-records")',
        "# Route removed.",
        "Delete the unauthenticated diagnostic route that dumps stored records.",
    ),
    (
        "ns-2",
        "terraform",
        'public_access_prevention = "inherited"\nmember = "allUsers"',
        'public_access_prevention = "enforced"',
        "Enforce public access prevention and remove every grant to allUsers.",
    ),
]


def init_db() -> None:
    """Create the control tables and seed them."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS im8_controls (
        control_id TEXT PRIMARY KEY,
        title TEXT,
        control_group TEXT,
        profile_level TEXT,
        statement TEXT,
        guidance TEXT,
        source TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remediation_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        control_id TEXT,
        file_type TEXT,
        vulnerable_pattern TEXT,
        compliant_replacement TEXT,
        explanation TEXT,
        FOREIGN KEY(control_id) REFERENCES im8_controls(control_id)
    )
    """)

    cursor.executemany("""
    INSERT OR REPLACE INTO im8_controls
    (control_id, title, control_group, profile_level, statement, guidance, source)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, CONTROLS)

    cursor.execute("DELETE FROM remediation_templates")
    cursor.executemany("""
    INSERT INTO remediation_templates
    (control_id, file_type, vulnerable_pattern, compliant_replacement, explanation)
    VALUES (?, ?, ?, ?, ?)
    """, TEMPLATES)

    conn.commit()
    conn.close()
    print(f"Seeded {len(CONTROLS)} IM8 Reform controls into {DB_FILE}.")


if __name__ == "__main__":
    init_db()
