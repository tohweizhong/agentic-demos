#!/bin/bash

# Set your Google Cloud Project ID, Location, Collection ID, and SDP Policy full resource name
PROJECT_ID="weizhong-project03"
LOCATION="us" # or 'us', 'eu'
COLLECTION_ID="sharepoint-us-apr26_1776086514433"

# Example full policy resource name: "projects/${PROJECT_ID}/locations/${LOCATION}/contentPolicies/${POLICY_ID}"
SDP_POLICY="projects/${PROJECT_ID}/locations/${LOCATION}/contentPolicies/sdp-policy-us-2-apr26"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Assigning SDP Content Policy to Data Connector..."

# The PATCH request
curl -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "https://us-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}/dataConnector?updateMask=dataProtectionPolicy" \
  -d '{
  "dataProtectionPolicy": {
    "sensitiveDataProtectionPolicy": {}
  }
}'
