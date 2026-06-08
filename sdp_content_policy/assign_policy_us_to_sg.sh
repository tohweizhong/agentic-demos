#!/bin/bash

# Set your Google Cloud Project ID, Singapore Connector details, and US SDP Policy details
PROJECT_ID="weizhong-project03"
CONNECTOR_LOCATION="sg"
POLICY_LOCATION="us"
COLLECTION_ID="sharepoint-sg-2-apr26_1777961646884"
POLICY_ID="sdp-policy-us-1-apr26"

# Example full policy resource name: "projects/${PROJECT_ID}/locations/${POLICY_LOCATION}/contentPolicies/${POLICY_ID}"
# Here we specify a policy created in the 'us' region
SDP_POLICY="projects/${PROJECT_ID}/locations/${POLICY_LOCATION}/contentPolicies/${POLICY_ID}"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Assigning US SDP Content Policy (${SDP_POLICY}) to Singapore Data Connector..."

# The PATCH request to Singapore Discovery Engine endpoint
curl -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "https://${CONNECTOR_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${CONNECTOR_LOCATION}/collections/${COLLECTION_ID}/dataConnector?updateMask=dataProtectionPolicy" \
  -d '{
  "dataProtectionPolicy": {
    "sensitiveDataProtectionPolicy": {
      "policy": "'"${SDP_POLICY}"'"
    }
  }
}'
