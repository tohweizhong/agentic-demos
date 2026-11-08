#!/usr/bin/env bash
# Prints the recent IAP decisions for agent egress, and the gateway requests.
#
# Usage: scripts/read_audit_log.sh [FRESHNESS]   (default: 30m)
#
# - IAP Data Access audit log: one entry for each decision. In DRY_RUN, the entry
#   has dryRun=true. A denied call has granted=false.
# - Gateway request log: one entry for each request through the gateway. An
#   enforced IAP denial does not always show here. Use the IAP log as the proof.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need terraform gcloud

FRESHNESS="${1:-30m}"
PROJECT="$(tf_output project_id)"

echo "== IAP decisions (cloudaudit.googleapis.com/data_access, iap.googleapis.com) =="
gcloud logging read \
  "logName=\"projects/${PROJECT}/logs/cloudaudit.googleapis.com%2Fdata_access\" AND protoPayload.serviceName=\"iap.googleapis.com\" AND protoPayload.authorizationInfo.permission:\"egressViaIAP\"" \
  --project="${PROJECT}" --freshness="${FRESHNESS}" --limit=20 \
  --format="table(timestamp, protoPayload.authorizationInfo[0].granted:label=GRANTED, protoPayload.metadata.dryRun:label=DRY_RUN, protoPayload.authorizationInfo[0].permission:label=PERMISSION, protoPayload.resourceName:label=RESOURCE)"

echo
echo "== Gateway requests (networkservices.googleapis.com/gateway_requests) =="
gcloud logging read \
  "logName=\"projects/${PROJECT}/logs/networkservices.googleapis.com%2Fgateway_requests\"" \
  --project="${PROJECT}" --freshness="${FRESHNESS}" --limit=20 \
  --format="table(timestamp, httpRequest.status:label=STATUS, jsonPayload.agentGatewayInfo.mcpInfo.parameter:label=MCP, jsonPayload.authzPolicyInfo.result:label=AUTHZ)"
