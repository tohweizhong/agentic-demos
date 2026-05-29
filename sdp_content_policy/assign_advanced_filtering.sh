#!/bin/bash

echo "This script has nothing to do with SDP or Content Policy. This applies a filter on a Fed connector, to ignore all files in Sharepoint with a certain MIPS label."

# Set your Google Cloud Project ID, Location, Collection ID, and SDP Policy full resource name
PROJECT_ID="weizhong-project03"
LOCATION="us" # or 'us', 'eu'
COLLECTION_ID="sharepoint-us-apr26_1776086514433"
MSIP_LABEL_GUID="defa4170-0d19-0005-0007-bc88714345d2"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Applying filter to Data Connector to ignore files with certain MIPS label..."

# The PATCH request
curl -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://us-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}/dataConnector?update_mask=params" \
  -d @- <<EOF
{
  "name": "projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}/dataConnector",
  "params": {
    "structured_search_filter": {
      "Path": ["https://weizhongt.sharepoint.com/sites/sharepoint-site-demo1"],
      "IsDocument": ["1"],
      "-InformationProtectionLabelId": ["${MSIP_LABEL_GUID}"]
    }
  }
}
EOF
