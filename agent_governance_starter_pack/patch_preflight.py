import sys

with open('scripts/preflight.sh', 'r') as f:
    content = f.read()

disk_check = """DISK_FREE_MB="$(df -Pm "${TF_DIR}" | awk 'NR==2 {print $4}' 2>/dev/null || echo "10000")"
"""
content = content.replace('TF_ADC_FIX="export GOOGLE_APPLICATION_CREDENTIALS=${ADC_FILE}"\nfi\n', 'TF_ADC_FIX="export GOOGLE_APPLICATION_CREDENTIALS=${ADC_FILE}"\nfi\n\n' + disk_check)

old_jq_args = """  --arg tf_adc_source "${TF_ADC_SOURCE}" \\
  --arg tf_adc_fix "${TF_ADC_FIX}" \\"""
new_jq_args = """  --arg tf_adc_source "${TF_ADC_SOURCE}" \\
  --arg tf_adc_fix "${TF_ADC_FIX}" \\
  --argjson disk_free_mb "${DISK_FREE_MB}" \\"""
content = content.replace(old_jq_args, new_jq_args)

old_blockers = """      (if $tf_adc_source == "none" then"""
new_blockers = """      (if $disk_free_mb < 250 then
        "Free disk space in terraform/ is " + ($disk_free_mb | tostring) + " MB (< 250 MB). Free disk space before running Terraform so terraform.tfstate is not truncated."
       else empty end),
      (if $tf_adc_source == "none" then"""
content = content.replace(old_blockers, new_blockers)

old_warnings = """      (if ($needs_ma_roles and $drs_legacy_restricted and ($ma_roles_count < 3) and $allow_gmm) then"""
new_warnings = """      (if ($disk_free_mb >= 250 and $disk_free_mb < 1024) then
        "Free disk space in terraform/ is " + ($disk_free_mb | tostring) + " MB (< 1024 MB). Free up space soon."
       else empty end),
      (if ($needs_ma_roles and $drs_legacy_restricted and ($ma_roles_count < 3) and $allow_gmm) then"""
content = content.replace(old_warnings, new_warnings)

old_json = """    project: {
      project_id: $project,
      project_number: $project_number,
      lifecycle_state: $lifecycle,
      region: $region,
      name_prefix: $prefix
    },"""
new_json = """    project: {
      project_id: $project,
      project_number: $project_number,
      lifecycle_state: $lifecycle,
      region: $region,
      name_prefix: $prefix
    },
    disk_free_mb: $disk_free_mb,"""
content = content.replace(old_json, new_json)

with open('scripts/preflight.sh', 'w') as f:
    f.write(content)
