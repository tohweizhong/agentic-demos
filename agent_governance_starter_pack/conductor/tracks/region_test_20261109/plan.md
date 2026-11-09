# Plan and Results: Live Test in asia-southeast1

An agent ran this test on 09 Nov 2026 from a fresh clone of `main`, in one project, with
`region = "asia-southeast1"` and all five governance tiers on. The repository owner did not test
it by hand. The first live test, in `us-central1` on 08 Nov 2026, is in
[mini_build_20261108](../mini_build_20261108/plan.md).

## Settings

| Variable | Value |
|---|---|
| `region` | `asia-southeast1` |
| `model_id` | `gemini-3.5-flash` |
| `model_location` | `asia-southeast1` |
| `malicious_uri.enforcement` (`policies/model_armor.yaml`) | `DISABLED` (see defect 1) |
| Tier variables | All `true` |
| `iap_enforcement_mode` | `DRY_RUN`, then `ENFORCE`, then `DRY_RUN` |
| Domain restricted sharing | Approach 2 (a short project exception through Terraform, then removed) |

## Results

| # | Test | Result | Evidence |
|---|---|---|---|
| 1 | `scripts/preflight.sh` | Expected `NO_GO` | One blocker: domain restricted sharing, before Approach 2. Fixed in this track (defect 4) |
| 2 | `terraform test`, plan, and apply | Pass, after a fix | 12 of 12 tests. The first apply stopped on the malicious URI filter (defect 1) |
| 3 | Read a work item (`get_status`) | Pass, after an IAM wait | The first queries failed for about 4 minutes after the apply (defect 2) |
| 4 | Write in `DRY_RUN` (`update_status`) | Pass | The tool call succeeded |
| 5 | Prompt injection at the ingress gateway | Pass | `403 Model Armor: Prompt violates content security configurations` |
| 6 | Prompt injection in a tool call (egress) | Pass, by inference | A base64-encoded injection passed the ingress screen. The tool call that carried the decoded text failed, and the MCP server got no `tools/call`. No log row confirms which control blocked it |
| 7 | Write in `ENFORCE` | Pass | `get_status` worked. `update_status` failed, and the MCP server got no `tools/call` |
| 8 | Audit logs | Known gap | Same as the README warning: the IAP log shows only MCP base methods, and the gateway log has no `403` row |
| 9 | Back to `DRY_RUN` | Pass | `terraform plan` showed no changes |

## Apply times

| Step | Time |
|---|---|
| First apply (stopped on defect 1) | 7 min 48 s for 47 of 57 resources. Egress gateway 2 min 52 s. IAP policy 3 min 12 s |
| Second apply | 5 min 41 s. Agent 4 min 59 s. Egress Model Armor policy 3 min 22 s |
| Remove the Approach 2 exception | 2.5 s |
| Switch to `ENFORCE` | 2 min 23 s |
| Switch back to `DRY_RUN` | 3 min 13 s |

## Defects and fixes

| # | Defect | Fix in this track |
|---|---|---|
| 1 | Model Armor in `asia-southeast1` rejects the malicious URI filter: `Error 400: Region 'asia-southeast1' does not support the requested capabilities: 'Malicious URI filter'`. The error also occurs when the filter is `DISABLED` | `terraform/gateway.tf` sends the field only when `malicious_uri.enforcement` is `ENABLED`. The default stays `ENABLED`. GUIDE Section 4 says to set it to `DISABLED` in `asia-southeast1` |
| 2 | Just after an apply, the agent gets `403 iam.serviceAccounts.getOpenIdToken` for the MCP invoker account, runs without its tools, and returns `MALFORMED_FUNCTION_CALL` | A GUIDE troubleshooting row: wait 3 to 5 minutes |
| 3 | `runbooks/switch_policy_mode.md` named the wrong resource in the expected plan | The runbook names `google_network_services_authz_extension.iap[0]` and gives the apply time |
| 4 | `scripts/preflight.sh` reported `NO_GO` when Approach 2 was set, and named "Option B or Option C" | Preflight reads `allow_google_managed_members`, reports a warning instead of a blocker when it is `true`, and uses the GUIDE approach names |
| 5 | GUIDE presented `us-central1` as the only region and did not mention `model_id` or `model_location` | New GUIDE subsection "Regions other than us-central1" |

Open observation: the agent log has repeated `400 Invalid project id in name!` errors from the
OpenTelemetry Cloud Trace exporter. The agent still works. The cause is not known.
