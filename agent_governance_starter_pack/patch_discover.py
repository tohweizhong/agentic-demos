import sys

with open('scripts/discover.sh', 'r') as f:
    content = f.read()

# Update identity_type and effective_identity
old_agents = """AGENTS="$(get "https://${REGION}-aiplatform.googleapis.com/v1beta1/${L}/reasoningEngines?pageSize=100" | jq '[.reasoningEngines[]? | {
  name: (.name | split("/") | last), display_name: .displayName,
  identity_type: (.spec.identityType // "SERVICE_AGENT (default)"),"""

new_agents = """AGENTS="$(get "https://${REGION}-aiplatform.googleapis.com/v1beta1/${L}/reasoningEngines?pageSize=100" | jq '[.reasoningEngines[]? | {
  name: (.name | split("/") | last), display_name: .displayName,
  effective_identity: (.spec.effectiveIdentity // empty),
  identity_type: (.spec.identityType // "SERVICE_ACCOUNT"),"""
  
content = content.replace(old_agents, new_agents)

with open('scripts/discover.sh', 'w') as f:
    f.write(content)
