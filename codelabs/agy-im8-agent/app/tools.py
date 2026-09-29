import os
import re
from datetime import datetime, timedelta, timezone

# Singapore Standard Time. The host clock runs in UTC.
_SGT = timezone(timedelta(hours=8))

# Comment lines that mark a planted defect. They must go when the defect goes.
_STALE_MARKER = re.compile(
    r'^[ \t]*(#|//)[ \t]*(VIOLATION|Non-compliant)\b.*\n',
    re.MULTILINE | re.IGNORECASE,
)


def _strip_stale_markers(text: str) -> str:
    """Remove violation marker comments left behind after a repair."""
    return _STALE_MARKER.sub("", text)


def audit_code_security(target_repo: str = "sample_target_repo", remediate: bool = False) -> str:
    """Audit application source code against IM8 Reform controls as-8 and lm-19.

    as-8 is Secrets Management. lm-19 is Log Sanitisation.

    Args:
        target_repo: Relative or absolute path to the target repository.
        remediate: If True, automatically apply compliant code fixes in place.

    Returns:
        A detailed summary of code security findings and remediation actions.
    """
    base_dir = os.path.abspath(target_repo)
    results = []

    # 1. Control as-8 in service/config.yaml
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
                new_content = _strip_stale_markers(new_content)
                with open(config_file, "w") as f:
                    f.write(new_content)

                # Verify the repair. Never report success without proof.
                if re.search(r'apex-sec-prod-[0-9]+', open(config_file).read()):
                    results.append("[as-8: Secrets Management] REMEDIATION FAILED. A plaintext secret remains in service/config.yaml.")
                else:
                    results.append("[as-8: Secrets Management] REMEDIATED. Replaced the static APEX secret in service/config.yaml with the environment variable ${APEX_SERVICE_KEY}.")
            else:
                results.append("[as-8: Secrets Management] VIOLATION DETECTED. Hardcoded APEX secret found in service/config.yaml.")
        else:
            results.append("[as-8: Secrets Management] COMPLIANT. No plaintext secrets found in service/config.yaml.")
    else:
        results.append(f"[as-8: Secrets Management] SKIPPED. Config file not found at {config_file}.")

    # 2. Control lm-19 in service/app.py
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
                new_app_content = _strip_stale_markers(new_app_content)
                with open(app_file, "w") as f:
                    f.write(new_app_content)

                # Verify the repair. Never report success without proof.
                if re.search(unmasked_pattern, open(app_file).read()):
                    results.append("[lm-19: Log Sanitisation] REMEDIATION FAILED. Unmasked citizen data remains in service/app.py.")
                else:
                    results.append("[lm-19: Log Sanitisation] REMEDIATED. Masked the citizen NRIC and phone number before logging in service/app.py.")
            else:
                results.append("[lm-19: Log Sanitisation] VIOLATION DETECTED. Unmasked citizen NRIC and phone number logged in service/app.py.")
        else:
            results.append("[lm-19: Log Sanitisation] COMPLIANT. Citizen PII is properly masked in service/app.py.")
    else:
        results.append(f"[lm-19: Log Sanitisation] SKIPPED. App file not found at {app_file}.")

    return "\n".join(results)


def audit_infra_security(target_repo: str = "sample_target_repo", remediate: bool = False) -> str:
    """Audit endpoints and infrastructure against IM8 Reform controls as-13 and ns-2.

    as-13 is Exposure of Internal System Details. ns-2 is Access Restrictions on
    CSP Resources Outside Virtual Network.

    Args:
        target_repo: Relative or absolute path to the target repository.
        remediate: If True, automatically apply compliant infrastructure fixes in place.

    Returns:
        A detailed summary of infrastructure security findings and remediation actions.
    """
    base_dir = os.path.abspath(target_repo)
    results = []

    # 1. Control as-13 in service/app.py
    app_file = os.path.join(base_dir, "service", "app.py")
    if os.path.exists(app_file):
        with open(app_file, "r") as f:
            app_content = f.read()

        debug_route_pattern = r'@app\.get\("/api/v1/debug/dump-records"\)\s*def dump_all_records\(\):[\s\S]*?return\s*\{[\s\S]*?\}'
        if re.search(debug_route_pattern, app_content):
            if remediate:
                replacement_comment = "# REMOVED: Unauthenticated debug endpoint removed for IM8 Reform control as-13"
                new_app_content = re.sub(debug_route_pattern, replacement_comment, app_content)
                new_app_content = _strip_stale_markers(new_app_content)
                with open(app_file, "w") as f:
                    f.write(new_app_content)

                # Verify the repair. Never report success without proof.
                if re.search(debug_route_pattern, open(app_file).read()):
                    results.append("[as-13: Exposure of Internal System Details] REMEDIATION FAILED. The debug route remains in service/app.py.")
                else:
                    results.append("[as-13: Exposure of Internal System Details] REMEDIATED. Removed the unauthenticated /api/v1/debug/dump-records route from service/app.py.")
            else:
                results.append("[as-13: Exposure of Internal System Details] VIOLATION DETECTED. Unauthenticated debug route found in service/app.py.")
        else:
            results.append("[as-13: Exposure of Internal System Details] COMPLIANT. No unauthenticated diagnostic endpoints found.")
    else:
        results.append(f"[as-13: Exposure of Internal System Details] SKIPPED. App file not found at {app_file}.")

    # 2. Control ns-2 in infra/terraform/storage.tf
    tf_file = os.path.join(base_dir, "infra", "terraform", "storage.tf")
    if os.path.exists(tf_file):
        with open(tf_file, "r") as f:
            tf_content = f.read()

        # Match both Terraform styles: iam_binding (members list) and iam_member (single member).
        public_principal = r'"(allUsers|allAuthenticatedUsers)"'
        has_public_binding = bool(
            re.search(r'members\s*=\s*\[\s*' + public_principal, tf_content)
            or re.search(r'member\s*=\s*' + public_principal, tf_content)
        )
        has_inherited = 'public_access_prevention = "inherited"' in tf_content

        if has_public_binding or has_inherited:
            if remediate:
                tf_clean = tf_content.replace(
                    'public_access_prevention = "inherited"',
                    'public_access_prevention = "enforced"'
                )
                # Remove any storage bucket IAM resource that grants public access.
                tf_clean = re.sub(
                    r'(?:#[^\n]*\n)*resource\s+"google_storage_bucket_iam_(?:binding|member)"\s+"[^"]+"\s*\{[^{}]*'
                    + public_principal + r'[^{}]*\}\n?',
                    '# REMOVED: public access binding removed for IM8 Reform control ns-2\n',
                    tf_clean
                )
                tf_clean = _strip_stale_markers(tf_clean)
                with open(tf_file, "w") as f:
                    f.write(tf_clean)

                # Verify the repair. Never report success without proof.
                with open(tf_file, "r") as f:
                    verify = f.read()
                still_public = bool(
                    re.search(r'members\s*=\s*\[\s*' + public_principal, verify)
                    or re.search(r'member\s*=\s*' + public_principal, verify)
                    or 'public_access_prevention = "inherited"' in verify
                )
                if still_public:
                    results.append("[ns-2: Access Restrictions on CSP Resources] REMEDIATION FAILED. Public access settings remain in infra/terraform/storage.tf. Manual review is required.")
                else:
                    results.append("[ns-2: Access Restrictions on CSP Resources] REMEDIATED. Enforced bucket access prevention and removed the public access binding in infra/terraform/storage.tf.")
            else:
                results.append("[ns-2: Access Restrictions on CSP Resources] VIOLATION DETECTED. Public bucket binding and inherited access prevention found in infra/terraform/storage.tf.")
        else:
            results.append("[ns-2: Access Restrictions on CSP Resources] COMPLIANT. Storage bucket is private and enforced.")
    else:
        results.append(f"[ns-2: Access Restrictions on CSP Resources] SKIPPED. Terraform file not found at {tf_file}.")

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


def get_assessment_timestamp() -> str:
    """Return the current date and time in Singapore Standard Time.

    Call this before you write the attestation report. Never guess the date.

    Returns:
        The timestamp as a string, for example "21 Sep 2026 17:39 SGT".
    """
    return datetime.now(_SGT).strftime("%d %b %Y %H:%M SGT")
