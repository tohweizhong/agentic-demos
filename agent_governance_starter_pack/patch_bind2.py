import sys
import re

with open('scripts/bind_existing_agent.sh', 'r') as f:
    content = f.read()

# Replace from GW_CONFIG to EOF
content = re.sub(r'GW_CONFIG="\{\}".*', r"""
echo "Run this command to recreate the agent with the new gateway bindings:"
echo "curl -X POST -H \\"Authorization: Bearer \\$(gcloud auth print-access-token)\\" \\\\"
echo "  -H \\"Content-Type: application/json\\" -H \\"x-goog-user-project: ${PROJECT}\\" \\\\"
echo "  \\"https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT}/locations/${REGION}/reasoningEngines?reasoning_engine_id=${DISP}-gw\\" \\\\"
echo "  -d '"

if [[ -n "${EGRESS_GW}" ]]; then
  body=$(echo "${body}" | jq --arg egw "projects/${PROJECT}/locations/${REGION}/agentGateways/${EGRESS_GW}" '
    .spec.deploymentSpec.agentGatewayConfig.agentToAnywhereConfig.agentGateway = $egw |
    .spec.packageSpec.imageSpec.buildArgs.AGENT_GATEWAY_ROOT_CERTIFICATES = "-----BEGIN CERTIFICATE-----\\n...\\n-----END CERTIFICATE-----"
  ')
fi
if [[ -n "${INGRESS_GW}" ]]; then
  body=$(echo "${body}" | jq --arg igw "projects/${PROJECT}/locations/${REGION}/agentGateways/${INGRESS_GW}" '
    .spec.deploymentSpec.agentGatewayConfig.clientToAgentConfig.agentGateway = $igw
  ')
fi

# Clean up read-only fields so it can be POSTed
body=$(echo "${body}" | jq 'del(.name, .createTime, .updateTime, .etag)')
echo "${body}"
echo "'"
""", content, flags=re.DOTALL)

with open('scripts/bind_existing_agent.sh', 'w') as f:
    f.write(content)
