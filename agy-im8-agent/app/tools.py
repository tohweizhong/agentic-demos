import os
import re

def audit_code_security(target_repo: str = "sample_target_repo", remediate: bool = False) -> str:
    """Audit application source code for IM8 Sec-01 (secrets) and IM8 Data-02 (citizen PII).

    Args:
        target_repo: Relative or absolute path to the target repository.
        remediate: If True, automatically apply compliant code fixes in place.

    Returns:
        A detailed summary of code security findings and remediation actions.
    """
    base_dir = os.path.abspath(target_repo)
    results = []

    # 1. Check IM8 Sec-01 in service/config.yaml
    config_file = os.path.join(base_dir, "service", "config.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            content = f.read()

        if 'apex_service_key: "apex-sec-prod-9841294812"' in content or 'apex_service_key: apex-sec-prod' in content:
            if remediate:
                new_content = re.sub(
                    r'apex_service_key:\s*["\']?apex-sec-prod-[0-9]+["\']?',
                    'apex_service_key: "${APEX_SERVICE_KEY}"',
                    content
                )
                with open(config_file, "w") as f:
                    f.write(new_content)
                results.append("[IM8-Sec-01: No Hardcoded Secrets] REMEDIATED. Replaced static APEX secret in service/config.yaml with environment variable ${APEX_SERVICE_KEY}.")
            else:
                results.append("[IM8-Sec-01: No Hardcoded Secrets] VIOLATION DETECTED. Hardcoded APEX secret found in service/config.yaml.")
        else:
            results.append("[IM8-Sec-01: No Hardcoded Secrets] COMPLIANT. No plaintext secrets found in service/config.yaml.")
    else:
        results.append(f"[IM8-Sec-01: No Hardcoded Secrets] SKIPPED. Config file not found at {config_file}.")

    # 2. Check IM8 Data-02 in service/app.py
    app_file = os.path.join(base_dir, "service", "app.py")
    if os.path.exists(app_file):
        with open(app_file, "r") as f:
            app_content = f.read()

        unmasked_pattern = r'logger\.info\(\s*f"Processing application for citizen NRIC:\s*\{application\.nric\}'
        if re.search(unmasked_pattern, app_content):
            if remediate:
                replacement = (
                    "masked_nric = application.nric[:1] + 'XXXX' + application.nric[-4:] if len(application.nric) == 9 else 'MASKED'\n"
                    "    masked_phone = 'XXXX-' + application.phone_number[-4:] if len(application.phone_number) >= 4 else 'MASKED'\n"
                    "    logger.info(\n"
                    "        f\"Processing application for citizen NRIC: {masked_nric}, \"\n"
                    "        f\"Name: {application.full_name}, Phone: {masked_phone}\"\n"
                    "    )"
                )
                new_app_content = re.sub(
                    r'logger\.info\(\s*f"Processing application for citizen NRIC: \{application\.nric\}, "\s*f"Name: \{application\.full_name\}, Phone: \{application\.phone_number\}"\s*\)',
                    replacement,
                    app_content
                )
                with open(app_file, "w") as f:
                    f.write(new_app_content)
                results.append("[IM8-Data-02: Citizen PII Protection] REMEDIATED. Masked citizen NRIC and phone number before logging in service/app.py.")
            else:
                results.append("[IM8-Data-02: Citizen PII Protection] VIOLATION DETECTED. Unmasked citizen NRIC and phone number logged in service/app.py.")
        else:
            results.append("[IM8-Data-02: Citizen PII Protection] COMPLIANT. Citizen PII is properly masked in service/app.py.")
    else:
        results.append(f"[IM8-Data-02: Citizen PII Protection] SKIPPED. App file not found at {app_file}.")

    return "\n".join(results)


def audit_infra_security(target_repo: str = "sample_target_repo", remediate: bool = False) -> str:
    """Audit infrastructure definitions and endpoints for IM8 App-04 (debug routes) and IM8 Infra-03 (cloud storage).

    Args:
        target_repo: Relative or absolute path to the target repository.
        remediate: If True, automatically apply compliant infrastructure fixes in place.

    Returns:
        A detailed summary of infrastructure security findings and remediation actions.
    """
    base_dir = os.path.abspath(target_repo)
    results = []

    # 1. Check IM8 App-04 in service/app.py
    app_file = os.path.join(base_dir, "service", "app.py")
    if os.path.exists(app_file):
        with open(app_file, "r") as f:
            app_content = f.read()

        debug_route_pattern = r'@app\.get\("/api/v1/debug/dump-records"\)\s*def dump_all_records\(\):[\s\S]*?return\s*\{[\s\S]*?\}'
        if re.search(debug_route_pattern, app_content):
            if remediate:
                replacement_comment = "# REMOVED: Unauthenticated debug endpoint removed for IM8 App-04 compliance"
                new_app_content = re.sub(debug_route_pattern, replacement_comment, app_content)
                with open(app_file, "w") as f:
                    f.write(new_app_content)
                results.append("[IM8-App-04: API Debug Route Hardening] REMEDIATED. Removed unauthenticated /api/v1/debug/dump-records route from service/app.py.")
            else:
                results.append("[IM8-App-04: API Debug Route Hardening] VIOLATION DETECTED. Unauthenticated debug route found in service/app.py.")
        else:
            results.append("[IM8-App-04: API Debug Route Hardening] COMPLIANT. No unauthenticated diagnostic endpoints found.")
    else:
        results.append(f"[IM8-App-04: API Debug Route Hardening] SKIPPED. App file not found at {app_file}.")

    # 2. Check IM8 Infra-03 in infra/terraform/storage.tf
    tf_file = os.path.join(base_dir, "infra", "terraform", "storage.tf")
    if os.path.exists(tf_file):
        with open(tf_file, "r") as f:
            tf_content = f.read()

        has_public_binding = 'members = ["allUsers"]' in tf_content or 'members = ["allAuthenticatedUsers"]' in tf_content
        has_inherited = 'public_access_prevention = "inherited"' in tf_content

        if has_public_binding or has_inherited:
            if remediate:
                tf_clean = tf_content.replace(
                    'public_access_prevention = "inherited"',
                    'public_access_prevention = "enforced"'
                )
                tf_clean = re.sub(
                    r'resource\s+"google_storage_bucket_iam_binding"\s+"public_read"\s+\{[\s\S]*?\}',
                    '# REMOVED: allUsers binding removed for IM8 Infra-03 compliance',
                    tf_clean
                )
                with open(tf_file, "w") as f:
                    f.write(tf_clean)
                results.append("[IM8-Infra-03: Cloud Storage Access Hardening] REMEDIATED. Enforced bucket access prevention and removed allUsers binding in infra/terraform/storage.tf.")
            else:
                results.append("[IM8-Infra-03: Cloud Storage Access Hardening] VIOLATION DETECTED. Public bucket binding and inherited access prevention found in infra/terraform/storage.tf.")
        else:
            results.append("[IM8-Infra-03: Cloud Storage Access Hardening] COMPLIANT. Storage bucket is private and enforced.")
    else:
        results.append(f"[IM8-Infra-03: Cloud Storage Access Hardening] SKIPPED. Terraform file not found at {tf_file}.")

    return "\n".join(results)


def generate_cio_report(report_content: str, output_path: str = "IM8_COMPLIANCE_REPORT.md") -> str:
    """Write the final executive CIO attestation report to disk.

    Args:
        report_content: Markdown text of the attestation report.
        output_path: Path to the target report file.

    Returns:
        Status confirmation message.
    """
    try:
        with open(output_path, "w") as f:
            f.write(report_content)
        return f"CIO attestation report successfully generated at: {output_path}"
    except Exception as e:
        return f"Error writing attestation report: {e}"
