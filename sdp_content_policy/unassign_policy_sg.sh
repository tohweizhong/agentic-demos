#!/bin/bash

# Set your Google Cloud Project ID, Singapore Connector details
PROJECT_ID="weizhong-project03"
LOCATION="sg"
COLLECTION_ID="sharepoint-sg-2-apr26_1777961646884"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Un-assigning SDP Content Policy from Singapore Data Connector..."

# The PATCH request to Singapore Discovery Engine endpoint to clear the policy
curl -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "https://${LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}/dataConnector?updateMask=dataProtectionPolicy" \
  -d '{
  "dataProtectionPolicy": {
    "sensitiveDataProtectionPolicy": {}
  }
}'
