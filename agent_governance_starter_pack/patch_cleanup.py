import sys

with open('scripts/cleanup.sh', 'r') as f:
    content = f.read()

# Fix step 1
old_step1 = """    if [[ "${LOG_BUCKET_MODE}" == "keep" ]]; then
      echo "Detaching the audit log bucket from Terraform state before destroy (--keep-log-bucket)..."
      terraform -chdir="${TF_DIR}" state rm google_logging_project_bucket_config.audit 2>/dev/null || true
    fi
    echo "Running terraform destroy..."
    if ! terraform -chdir="${TF_DIR}" destroy -auto-approve; then"""

new_step1 = """    if [[ "${LOG_BUCKET_MODE}" == "keep" ]]; then
      echo "Detaching the audit log bucket from Terraform state before destroy (--keep-log-bucket)..."
      terraform -chdir="${TF_DIR}" state rm google_logging_project_bucket_config.audit 2>/dev/null || true
    fi
    
    # Fix for Problem 24: Remove deleted parents from state to avoid 403 on getIamPolicy during destroy
    STATE_LIST="$(terraform -chdir="${TF_DIR}" state list 2>/dev/null || true)"
    if echo "${STATE_LIST}" | grep -q "google_artifact_registry_repository_iam_member.mcp_build_writer"; then
      if ! gcloud artifacts repositories describe "${PREFIX}-mcp" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
        echo "Artifact Registry ${PREFIX}-mcp is already deleted. Removing from state..."
        terraform -chdir="${TF_DIR}" state rm google_artifact_registry_repository_iam_member.mcp_build_writer google_artifact_registry_repository.mcp 2>/dev/null || true
      fi
    fi
    if echo "${STATE_LIST}" | grep -q "google_cloud_run_v2_service_iam_member.mcp_invoker"; then
      if ! gcloud run services describe "${PREFIX}-work-items" --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
        echo "Cloud Run service ${PREFIX}-work-items is already deleted. Removing from state..."
        terraform -chdir="${TF_DIR}" state rm google_cloud_run_v2_service_iam_member.mcp_invoker google_cloud_run_v2_service.mcp 2>/dev/null || true
      fi
    fi

    echo "Running terraform destroy..."
    if ! terraform -chdir="${TF_DIR}" destroy -auto-approve; then"""

content = content.replace(old_step1, new_step1)

# Fix Step 8 (Artifact Registry and Cloud Run)
old_step8_ar = """  if gcloud artifacts repositories describe "${PREFIX}-mcp" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Artifact Registry ${PREFIX}-mcp..."
    gcloud artifacts repositories delete "${PREFIX}-mcp" --location="${REGION}" --project="${PROJECT}" --quiet || fail "Delete of Artifact Registry ${PREFIX}-mcp failed."
  fi"""

new_step8_ar = """  if gcloud artifacts repositories describe "${PREFIX}-mcp" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Artifact Registry ${PREFIX}-mcp..."
    gcloud artifacts repositories delete "${PREFIX}-mcp" --location="${REGION}" --project="${PROJECT}" --quiet || fail "Delete of Artifact Registry ${PREFIX}-mcp failed."
    terraform -chdir="${TF_DIR}" state rm google_artifact_registry_repository_iam_member.mcp_build_writer google_artifact_registry_repository.mcp 2>/dev/null || true
  fi"""
content = content.replace(old_step8_ar, new_step8_ar)

# Cloud Run
old_step8_run = """for cr_svc in "${PREFIX}-work-items" "${PREFIX}-echo"; do
  if gcloud run services describe "${cr_svc}" --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Cloud Run service ${cr_svc}..."
    gcloud run services delete "${cr_svc}" --region="${REGION}" --project="${PROJECT}" --quiet || fail "Delete of Cloud Run service ${cr_svc} failed."
  fi
done"""

new_step8_run = """for cr_svc in "${PREFIX}-work-items" "${PREFIX}-echo"; do
  if gcloud run services describe "${cr_svc}" --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Cloud Run service ${cr_svc}..."
    gcloud run services delete "${cr_svc}" --region="${REGION}" --project="${PROJECT}" --quiet || fail "Delete of Cloud Run service ${cr_svc} failed."
    if [[ "${cr_svc}" == "${PREFIX}-work-items" ]]; then
      terraform -chdir="${TF_DIR}" state rm google_cloud_run_v2_service_iam_member.mcp_invoker google_cloud_run_v2_service.mcp 2>/dev/null || true
    fi
  fi
done"""
content = content.replace(old_step8_run, new_step8_run)

with open('scripts/cleanup.sh', 'w') as f:
    f.write(content)
