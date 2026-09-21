import sqlite3

def init_db():
    """Initializes the SQLite database with official Singapore Government IM8 policies."""
    conn = sqlite3.connect("im8_policies.db")
    cursor = conn.cursor()

    # Create policies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS im8_policies (
        rule_id TEXT PRIMARY KEY,
        clause_title TEXT,
        domain TEXT,
        severity TEXT,
        requirement TEXT,
        remediation_guidance TEXT
    )
    """)

    # Create remediation templates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remediation_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id TEXT,
        file_type TEXT,
        vulnerable_pattern TEXT,
        compliant_replacement TEXT,
        explanation TEXT,
        FOREIGN KEY(rule_id) REFERENCES im8_policies(rule_id)
    )
    """)

    # Seed data: IM8 Core Policies
    policies_data = [
        (
            "IM8-Sec-01",
            "No Hardcoded Secrets",
            "Code Security",
            "CRITICAL",
            "Source code and configuration files must not contain plaintext API keys, passwords, or secret tokens. Static credentials must be extracted to environment variables or fetched from a secrets manager.",
            "Replace static credentials with environment variable lookups (for example, os.getenv('APEX_SERVICE_KEY')). Remove secrets from version control."
        ),
        (
            "IM8-Data-02",
            "Citizen PII Protection",
            "Data Protection",
            "HIGH",
            "Citizen National Registration Identity Card (NRIC) numbers and phone numbers must be masked in application logs and non-production outputs. Only the first letter and last 4 characters of NRIC may be visible (for example, SXXXX123A).",
            "Apply string masking logic before logging. Mask NRICs as SXXXX123A and phone numbers as XXXX-1234."
        ),
        (
            "IM8-App-04",
            "API Debug Route Hardening",
            "Application Security",
            "HIGH",
            "Administrative and diagnostic endpoints must not be exposed without strict authentication and authorization. Unprotected routes that dump database records or application memory must be disabled in production.",
            "Remove unauthenticated debug endpoints from production services, or protect them with administrative authorization guards."
        ),
        (
            "IM8-Infra-03",
            "Cloud Storage Access Hardening",
            "Infrastructure Security",
            "CRITICAL",
            "Cloud storage buckets hosting government workloads must enforce private access. Public read permissions ('allUsers' or 'allAuthenticatedUsers') and inherited access prevention are strictly prohibited on Government Commercial Cloud (GCC) buckets.",
            "Set public_access_prevention = 'enforced' and remove all storage bucket IAM bindings that grant access to allUsers or allAuthenticatedUsers."
        )
    ]

    for row in policies_data:
        cursor.execute("""
        INSERT OR REPLACE INTO im8_policies 
        (rule_id, clause_title, domain, severity, requirement, remediation_guidance)
        VALUES (?, ?, ?, ?, ?, ?)
        """, row)

    # Seed data: Remediation Templates
    templates_data = [
        (
            "IM8-Sec-01",
            "yaml",
            "apex_service_key: \"apex-sec-prod-9841294812\"",
            "apex_service_key: ${APEX_SERVICE_KEY}",
            "Replaced static APEX secret key with environment variable placeholder."
        ),
        (
            "IM8-Data-02",
            "python",
            "logger.info(f\"Processing application for citizen NRIC: {application.nric}, Name: {application.full_name}, Phone: {application.phone_number}\")",
            "masked_nric = application.nric[:1] + 'XXXX' + application.nric[-4:] if len(application.nric) == 9 else 'MASKED'\n    masked_phone = 'XXXX-' + application.phone_number[-4:] if len(application.phone_number) >= 4 else 'MASKED'\n    logger.info(f\"Processing application for citizen NRIC: {masked_nric}, Name: {application.full_name}, Phone: {masked_phone}\")",
            "Applied NRIC and telephone masking before logging citizen application data."
        ),
        (
            "IM8-App-04",
            "python",
            "@app.get(\"/api/v1/debug/dump-records\")\ndef dump_all_records():\n    return {\"count\": len(APPLICATIONS), \"records\": APPLICATIONS}",
            "# REMOVED: Unauthenticated debug endpoint removed for IM8 App-04 compliance",
            "Deleted unauthenticated diagnostic route dumping citizen database records."
        ),
        (
            "IM8-Infra-03",
            "terraform",
            "public_access_prevention = \"inherited\"\n\nresource \"google_storage_bucket_iam_binding\" \"public_read\" {\n  role    = \"roles/storage.objectViewer\"\n  members = [\"allUsers\"]\n}",
            "public_access_prevention = \"enforced\"",
            "Enforced public access prevention and removed allUsers object viewer binding."
        )
    ]

    for row in templates_data:
        cursor.execute("""
        INSERT OR REPLACE INTO remediation_templates
        (rule_id, file_type, vulnerable_pattern, compliant_replacement, explanation)
        VALUES (?, ?, ?, ?, ?)
        """, row)

    conn.commit()
    conn.close()
    print("IM8 Policy database initialized successfully!")

if __name__ == "__main__":
    init_db()
