#!/bin/bash

# Set your Google Cloud Project ID, Location, and Policy ID
PROJECT_ID="your-project-id"
LOCATION="global"
# Example policy ID: "test_policy1"
POLICY_ID="your_policy_id"

# Get your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "Creating SDP Content Policy..."

curl -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "https://dlp.googleapis.com/v2/projects/${PROJECT_ID}/locations/${LOCATION}/contentPolicies" \
  -d @- <<EOF
{
  "content_policy": {
    "inspect_template": {
      "display_name": "Sample Inspect Configuration for Content Policy",
      "inspect_config": {
        "info_types": [
          {
            "name": "CREDIT_CARD_NUMBER"
          }
        ],
        "custom_info_types": [
          {
            "info_type": {
              "name": "CUSTOM_MSIP1"
            },
            "likelihood": "VERY_LIKELY",
            "metadata_key_value_expression": {
              "key_regex": "MSIP_Label_.*_Enabled",
              "value_regex": "true"
            }
          }
        ],
        "min_likelihood": "POSSIBLE"
      }
    },
    "rules": {
      "conditions": {
        "info_type_condition": {
          "any_info_type": {}
        }
      },
      "return_verdict": "BLOCK"
    }
  },
  "content_policy_id": "${POLICY_ID}"
}
EOF
