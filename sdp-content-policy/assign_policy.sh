#!/bin/bash

# Set your Google Cloud Project ID, Location, Collection ID, and SDP Policy full resource name
PROJECT_ID="weizhong-project03"
LOCATION="global" # or 'us', 'eu'
COLLECTION_ID="jira-mar26-3_1772607027254"

# Example full policy resource name: "projects/${PROJECT_ID}/locations/${LOCATION}/contentPolicies/${POLICY_ID}"
SDP_POLICY="projects/weizhong-project03/locations/global/contentPolicies/test_policy1"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Assigning SDP Content Policy to Data Connector..."

# The PATCH request
curl -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}/dataConnector?updateMask=dataProtectionPolicy" \
  -d '{
  "dataProtectionPolicy": {
    "sensitiveDataProtectionPolicy": {
      "policy": "'"${SDP_POLICY}"'"
    }
  }
}'
