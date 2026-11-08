#!/usr/bin/env bash
# Step 4. Deploy the sample UI client to Cloud Run, protected by IAP.
#
# The client uses one fixed user ID for every browser session. A public URL
# would let any person read the GitHub data of the user who gave consent.
# For this reason the service has no public access. IAP lets only IAP_MEMBER
# open the client.
source "$(dirname "$0")/common.sh"
require AGENT_ID CLIENT_SERVICE CLIENT_SA_NAME BUILD_SA_NAME IAP_MEMBER

# Cloud Build builds the container image with its own service account. The
# script uses a dedicated build account, so the default compute service
# account needs no extra role.
if ! gcloud iam service-accounts describe "${BUILD_SA_EMAIL}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating build service account ${BUILD_SA_EMAIL}."
  gcloud iam service-accounts create "${BUILD_SA_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="Agent auth demo client build"
  sleep 15
fi
echo "Granting roles/cloudbuild.builds.builder to the build account."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SA_EMAIL}" \
  --role="roles/cloudbuild.builds.builder" \
  --condition=None >/dev/null

echo "Deploying ${CLIENT_SERVICE} from ${CLIENT_DIR}."
gcloud beta run deploy "${CLIENT_SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --source="${CLIENT_DIR}" \
  --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILD_SA_EMAIL}" \
  --service-account="${CLIENT_SA_EMAIL}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},AGENT_ID=${AGENT_ID}" \
  --no-allow-unauthenticated \
  --iap \
  --quiet

echo "Letting the IAP service agent invoke the service."
gcloud run services add-iam-policy-binding "${CLIENT_SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
  --role="roles/run.invoker" >/dev/null

echo "Granting IAP access to ${IAP_MEMBER}."
gcloud beta iap web add-iam-policy-binding \
  --project="${PROJECT_ID}" \
  --resource-type=cloud-run \
  --service="${CLIENT_SERVICE}" \
  --region="${REGION}" \
  --member="${IAP_MEMBER}" \
  --role="roles/iap.httpsResourceAccessor" \
  --condition=None >/dev/null

# A service has two URLs: the deterministic URL and an older hash URL.
# The agent continue URI uses the deterministic URL.
URLS="$(gcloud run services describe "${CLIENT_SERVICE}" \
  --project="${PROJECT_ID}" --region="${REGION}" \
  --format="value(metadata.annotations['run.googleapis.com/urls'])")"
echo
echo "Client URL: ${CLIENT_URL}"
if [[ "${URLS}" != *"${CLIENT_URL}"* ]]; then
  echo "WARNING: the service URLs are ${URLS}."
  echo "The agent continue URI uses ${CLIENT_URL}. Redeploy the agent with a correct URL."
fi
