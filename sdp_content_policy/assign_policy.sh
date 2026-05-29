#!/bin/bash

# Set your Google Cloud Project ID, Location, Collection ID, and SDP Policy full resource name
PROJECT_ID="weizhong-project03"
LOCATION="sg" # or 'us', 'eu'
COLLECTION_ID="sharepoint-sg-2-apr26_1777961646884"

# Example full policy resource name: "projects/${PROJECT_ID}/locations/${LOCATION}/contentPolicies/${POLICY_ID}"
SDP_POLICY="projects/${PROJECT_ID}/locations/${LOCATION}/contentPolicies/sdp-policy-sg-1-may26"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Assigning SDP Content Policy to Data Connector..."

# The PATCH request
curl -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "https://sg-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}/dataConnector?updateMask=dataProtectionPolicy" \
  -d '{
  "dataProtectionPolicy": {
    "sensitiveDataProtectionPolicy": {
      "policy": "'"${SDP_POLICY}"'"
    }
  }
}'
