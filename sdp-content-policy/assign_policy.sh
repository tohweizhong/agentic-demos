#!/bin/bash

# Set your Google Cloud Project ID, Location, Collection ID, and SDP Policy full resource name
PROJECT_ID="your-project-id"
LOCATION="global" # or 'us', 'eu'
COLLECTION_ID="your_connector_collection"

# Example full policy resource name: "projects/${PROJECT_ID}/locations/${LOCATION}/contentPolicies/${POLICY_ID}"
SDP_POLICY="your_sdp_content_policy_full_resource_name"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Assigning SDP Content Policy to Data Connector..."

# The PATCH request
curl -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}/dataConnector?updateMask=dataProtectionPolicy" \
  -d '{
  "dataProtectionPolicy": {
    "sensitiveDataProtectionPolicy": {
      "policy": "'"${SDP_POLICY}"'"
    }
  }
}'
