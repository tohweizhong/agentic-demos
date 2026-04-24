#!/bin/bash

echo "List config set up with a given connector."

# Set your Google Cloud Project ID, Location, Collection ID, and SDP Policy full resource name
PROJECT_ID="weizhong-project03"
LOCATION="us" # or 'us', 'eu'
COLLECTION_ID="sharepoint-us-apr26_1776086514433"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

curl -X GET \
-H "Authorization: Bearer ${ACCESS_TOKEN}" \
-H "X-Goog-User-Project: ${PROJECT_ID}" \
"https://us-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}/dataConnector"