import sys

with open('scripts/adoption_plan.sh', 'r') as f:
    content = f.read()

# Fix the jq for cloud_run
old_cloud_run = ".cloud_run[] | select(.name as $rn | (.registry"
new_cloud_run = ".registry as $reg | .cloud_run[] | select(.name as $rn | ($reg"
content = content.replace(old_cloud_run, new_cloud_run)

# Fix effective_identity lacking principal://
# previously I used `"  \"principal://\(.effective_identity)\","` but maybe it failed replacing?
# Let's just regex replace it
import re
content = re.sub(r'"  \\"\\\\\(.effective_identity\\)\\","', r'"  \\"principal://\(.effective_identity)\\","', content)

with open('scripts/adoption_plan.sh', 'w') as f:
    f.write(content)
