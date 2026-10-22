# Runbook: deploy the Agent Gateway governance demo

This runbook follows the public codelab. It adds the fixes for five problems that came up in a
real run and that the codelab does not mention. Each fix is marked **Fix**.

Placeholders:

| Placeholder | Meaning |
|---|---|
| `PROJECT_ID` | Your demo project ID |
| `PROJECT_NUMBER` | Your demo project number |
| `ORG_ID` | Your organization ID |
| `ADMIN_EMAIL` | The user that runs the demo |

Region: `us-central1`, the codelab default.

> [!TIP]
> Use a clean demo project in a sandbox organization. The codelab needs organization-level IAM.

---

## 1. Prepare Cloud Shell

Set the variables in each new Cloud Shell session. The scripts in later steps fail without them.

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export ORG_ID=$(gcloud projects get-ancestors $PROJECT_ID | awk '$2 == "organization" {print $1}')
export REGION=us-central1
echo $PROJECT_ID $PROJECT_NUMBER $ORG_ID
```

**Fix 1: Terraform can be missing from Cloud Shell.** Install it in your home folder, so that it
stays after Cloud Shell restarts:

```bash
TF_VER=$(curl -s https://checkpoint-api.hashicorp.com/v1/check/terraform | jq -r .current_version)
mkdir -p ~/bin
curl -sLo /tmp/tf.zip https://releases.hashicorp.com/terraform/${TF_VER}/terraform_${TF_VER}_linux_amd64.zip
unzip -o /tmp/tf.zip terraform -d ~/bin
echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc && export PATH=$HOME/bin:$PATH
terraform version   # must be 1.12.2 or later
```

## 2. Clone, bootstrap, and configure (codelab steps 2 to 6)

```bash
git clone https://github.com/GoogleCloudPlatform/cloud-networking-solutions.git
cd cloud-networking-solutions/demos/agent-gateway

gcloud services enable compute.googleapis.com serviceusage.googleapis.com \
  cloudresourcemanager.googleapis.com iam.googleapis.com storage.googleapis.com dns.googleapis.com

gcloud storage buckets create gs://${PROJECT_ID}-tfstate --location=${REGION} --uniform-bucket-level-access
cp terraform/example.backend.conf terraform/backend.conf
cp terraform/example.tfvars terraform/terraform.tfvars
```

Edit two files:

| File | Change |
|---|---|
| `terraform/backend.conf` | `bucket = "PROJECT_ID-tfstate"`, `prefix = "agent-gateway"` |
| `terraform/terraform.tfvars` | `project_id`, `organization_id` (number only), `platform_admin_members = ["user:ADMIN_EMAIL"]` |

Keep the other values. `agent_gateway_iap_iam_enforcement_mode = "DRY_RUN"` is correct for now.

## 3. Allow Google-managed accounts in IAM (before Terraform)

**Fix 2: domain restricted sharing blocks three grants.** The Terraform module gives Model Armor
roles to the gateway's Service Extensions service account. That account is in a Google-managed
project. If your organization uses domain restricted sharing (`iam.allowedPolicyMemberDomains`),
the grants fail with "do not belong to a permitted customer".

Allow all members on the demo project only:

```bash
gcloud services enable orgpolicy.googleapis.com --project=$PROJECT_ID
cat > /tmp/drs.yaml <<EOF
name: projects/${PROJECT_ID}/policies/iam.allowedPolicyMemberDomains
spec:
  rules:
  - allowAll: true
EOF
gcloud org-policies set-policy /tmp/drs.yaml
```

Wait about 2 minutes before you run Terraform.

> [!IMPORTANT]
> In a customer organization, the organization admin must approve this exception. Plan for it.

## 4. Deploy the infrastructure (codelab step 7)

```bash
cd terraform
terraform init -backend-config=backend.conf
terraform plan -out=tfplan
terraform apply tfplan
cd ..
```

The apply takes about 25 minutes. Most of the time is the gateway (about 6 minutes) and the
authorization policies (about 5 minutes each).

## 5. Build and deploy the MCP servers (codelab step 11)

```bash
export MCP_INGRESS=$(cd terraform && terraform output -raw mcp_cloud_run_ingress_annotation)
envsubst '${PROJECT_ID} ${REGION} ${MCP_INGRESS}' < skaffold.yaml.tmpl > skaffold.yaml
for f in cloudrun/*.yaml.tmpl; do
  envsubst '${PROJECT_ID} ${REGION} ${MCP_INGRESS}' < "$f" > "${f%.tmpl}"
done
grep -n '\${' skaffold.yaml cloudrun/*.yaml   # must print nothing

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="user:$(gcloud config get-value account)" --role="roles/iam.serviceAccountUser"
skaffold run
```

## 6. Deploy the agent (codelab step 12)

Grant all agents access to the registry endpoints. The agent needs them during deployment.

```bash
./scripts/grant_agent_mcp_egress.sh --bind-all-agents --endpoints
```

**Fix 3: the agent cannot trust the gateway certificate.** The gateway decrypts agent traffic and
signs it with its own CA. Agent Runtime adds that CA to the system trust store, but `httpx` uses
its own CA bundle. The agent then fails at startup with `CERTIFICATE_VERIFY_FAILED`, and the
deployment fails with code 13.

Add three environment variables to `env_vars` in `deploy_agent.py`, then deploy:

```bash
cd src/mortgage-agent
sed -i '/"ADK_ENABLE_MCP_GRACEFUL_ERROR_HANDLING": "true",/a\                "SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt",\n                "REQUESTS_CA_BUNDLE": "/etc/ssl/certs/ca-certificates.crt",\n                "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH": "/etc/ssl/certs/ca-certificates.crt",' deploy_agent.py
grep -c "ca-certificates.crt" deploy_agent.py   # must print 3

uv sync
uv run python deploy_agent.py \
  --project=${PROJECT_ID} --region=${REGION} \
  --enable-agent-identity --agent-name=mortgage-agent \
  --agent-gateway=projects/${PROJECT_ID}/locations/${REGION}/agentGateways/agent-gateway \
  --mcp-invoker-sa=$(terraform -chdir=../../terraform output -raw agent_mcp_invoker_email) \
  --model-endpoint-location=global
export AGENT_ID=<number from reasoningEngines/... in the output>
cd ../..
```

The deployment takes about 15 minutes.

## 7. Grant per-MCP egress (codelab step 13)

```bash
./scripts/grant_agent_mcp_egress.sh --mcp --agent-id ${AGENT_ID} \
  --mcp-filter "legacy-dms income-verification"

./scripts/grant_agent_mcp_egress.sh --mcp --agent-id ${AGENT_ID} \
  --mcp-filter "corporate-email" \
  --condition-expression "api.getAttribute('iap.googleapis.com/mcp.tool.isReadOnly', false) == true || api.getAttribute('iap.googleapis.com/mcp.toolName', '') == ''" \
  --condition-title "ReadOnlyToolsOnly" \
  --condition-description "Restrict ${AGENT_ID} to read-only tools on corporate-email"
```

**Fix 4: an unconditional grant cancels the read-only condition.** `deploy_agent.py` also gives
the agent an unconditional `roles/iap.egressor` on each MCP server. IAM adds bindings together, so
the agent can still call `send_email`.

Check the policy on `corporate-email`. Remove every binding without a condition, and keep only
`ReadOnlyToolsOnly`. Find the MCP server ID in the grant script output.

```bash
MCP=projects/${PROJECT_ID}/locations/${REGION}/iap_web/agentRegistry/mcpServers/<corporate-email-id>
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" -d '{"options":{"requestedPolicyVersion":3}}' \
  "https://iap.googleapis.com/v1/${MCP}:getIamPolicy" > policy.json
# Edit policy.json: delete the bindings that have no "condition". Then:
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" -d "{\"policy\": $(cat policy.json)}" \
  "https://iap.googleapis.com/v1/${MCP}:setIamPolicy"
```

## 8. Enforce IAP (codelab step 15)

```bash
cd terraform
sed -i 's/^agent_gateway_iap_iam_enforcement_mode = "DRY_RUN"/agent_gateway_iap_iam_enforcement_mode = null/' terraform.tfvars
terraform apply
```

**Fix 5: the update can fail with `ABORTED`.** The error is "There is another ongoing operation for
the same AgentGateway". In a real run, the update failed three times in a row, each time after about
5 minutes. A wait of 19 minutes before the third try did not help. So a plain retry does not fix it.

What worked: delete the two gateway policies, apply the change, and let Terraform create the
policies again. Without an attached policy, the extension update finished in 4 seconds.

```bash
terraform destroy -target='module.agent_gateway[0].google_network_security_authz_policy.iap'
terraform plan -out=tfplan_fix   # expect: 2 to add, 1 or 2 to change, 0 to destroy
terraform apply tfplan_fix
```

The destroy also deletes the Model Armor policy, because it depends on the IAP policy. Each policy
delete or create takes 5 to 8 minutes, so the full fix takes about 30 minutes.

> [!WARNING]
> While the policies are missing, the gateway **denies all agent traffic**. It does not let traffic
> pass. The gateway log shows the rule `default_denied` with action `DENIED`. The agent cannot even
> create a session. Do this fix only when nobody uses the demo.

Do not trust the extension setting alone. Check what the gateway really does in the request log:

```bash
gcloud logging read "logName=\"projects/${PROJECT_ID}/logs/networkservices.googleapis.com%2Fgateway_requests\" AND httpRequest.status=403" \
  --freshness=1h --limit=5 \
  --format="table(timestamp, jsonPayload.agentGatewayInfo.mcpInfo.parameter, jsonPayload.authzPolicyInfo.result, httpRequest.status)"
```

## 9. Register in Gemini Enterprise (codelab step 16)

1. Create a Gemini Enterprise app in the `global` location.
2. Add the agent as an Agent Engine agent, with the resource name
   `projects/PROJECT_NUMBER/locations/us-central1/reasoningEngines/AGENT_ID`.
3. Open the web app, then the Agent Gallery, and select Mortgage Assistant Agent.

## 10. Scale down and up between sessions

Almost all of the idle cost comes from the Cloud Run minimum instances. In a real run, the agent
showed no charge while it was idle. So you can normally leave the agent unchanged, and scale only
the MCP servers. Scale them up again at least 30 minutes before the next session.

```bash
# Scale down: MCP servers to 0 minimum instances
for s in legacy-dms income-verification corporate-email; do
  gcloud run services update $s --region=${REGION} --min-instances=0
done

# Optional, only if the Billing report shows an idle charge for the agent:
# agent to 0 minimum instances
curl -s -X PATCH \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${AGENT_ID}?updateMask=spec.deploymentSpec.minInstances" \
  -d '{"spec": {"deploymentSpec": {"minInstances": 0}}}'
```

To scale up, run the same commands with `1` for each MCP server and `2` for the agent.

| Note | Detail |
|---|---|
| Agent scale-down not tested | The agent command was not tested in a real run. A change to the agent settings can start a new rollout of the agent, so do it only when you have time to fix a problem. |
| Cold start | With 0 MCP instances, the first tool call takes about 16 to 19 seconds. This is longer than the 5-second MCP timeout, so the agent loses its tools for that request. |
| Terraform | A later `terraform apply` can set the Cloud Run minimum instances back to the value in `terraform.tfvars`. |

## 11. Track the cost

The Billing report shows the cost per SKU. Filter on your demo project and group by SKU.

To read the cost with one query, export the billing data to BigQuery:

1. Create a dataset in a project that you keep. Use the `US` or `EU` multi-region location. Then the
   export also loads the costs from the start of the previous month.

   ```bash
   bq mk --dataset --location=US ${PROJECT_ID}:billing_export
   ```

2. In the Billing console, open **Billing export**. Under **Standard usage cost**, select this
   dataset. This step has no API. You need the Billing Account Administrator role.
3. Wait a few hours for the first rows. The older costs can take up to 5 days to load.
4. Query the cost per day and per SKU. In the table name, replace the dashes in your billing account
   ID with underscores.

   ```sql
   SELECT
     DATE(usage_start_time) AS day,
     service.description AS service,
     sku.description AS sku,
     ROUND(SUM(cost) + SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)), 2) AS net_cost
   FROM `PROJECT_ID.billing_export.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX`
   WHERE project.id = "PROJECT_ID"
   GROUP BY day, service, sku
   ORDER BY day DESC, net_cost DESC
   ```

## 12. Clean up

If a deployment of the agent failed, delete that agent. Its IAP grants on the registry endpoints
then point to an agent that no longer exists. They do nothing, but they make the policies harder to
read in a demo, so remove them too.

To remove everything:

```bash
# 1. Delete the agent first. Delete the failed agents too, if any.
# 2. Then remove the infrastructure:
cd terraform && terraform destroy
# 3. Remove the project-level org policy exception:
gcloud org-policies delete iam.allowedPolicyMemberDomains --project=$PROJECT_ID
```
