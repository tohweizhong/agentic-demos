import sys

with open('scripts/adoption_plan.sh', 'r') as f:
    content = f.read()

# Fix the jq for cloud_run
old_cloud_run = "$.registry"
new_cloud_run = ".registry"
content = content.replace(old_cloud_run, new_cloud_run)

# Fix effective_identity lacking principal://
old_eff = '"  \\""\\(.effective_identity)\\","'
new_eff = '  "  \\"principal://\\(.effective_identity)\\","'
content = content.replace(old_eff, new_eff)

with open('scripts/adoption_plan.sh', 'w') as f:
    f.write(content)
