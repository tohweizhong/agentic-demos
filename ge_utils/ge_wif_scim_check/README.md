# WIF SCIM Tenant and Attribute Mapping Check

These scripts read a Workforce Identity Federation (WIF) setup, one step at a time. The
last step shows two facts for each provider:

1. If the provider has a SCIM tenant.
2. The attribute mapping of the provider. This tells you if `google.subject` keeps the case
   from the identity provider.

The scripts only read. They do not change anything.

## Explanation

* A workforce pool belongs to an **organization**. A provider belongs to a pool.
* A SCIM tenant belongs to a **provider**, not to a pool. The command
  `gcloud iam workforce-pools tenants list` does not exist. The correct command is
  `gcloud iam workforce-pools providers scim-tenants list`.
* The attribute mapping is also on the provider. `gcloud iam workforce-pools describe`
  shows the pool only, so its output does not include the mapping.
* Without a SCIM tenant, the agent Share dialog gives no suggestions. Users must type each
  address.
* If `google.subject` does not use `lowerAscii()`, Cloud IAM compares subjects with case
  sensitivity. A share to `jane_doe@example.com` then gives no access to the user
  `Jane_Doe@example.com`, and nobody sees an error.

## Prerequisites

* The [Google Cloud CLI](https://cloud.google.com/sdk/docs/install). Cloud Shell already
  has it. If `scim-tenants` is not found, run `gcloud components update`.
* Sign in with `gcloud auth login` as a user in the organization that owns the pool.
* A role on the **organization** that can read workforce pools and providers and list SCIM
  tenants, for example `roles/iam.workforcePoolAdmin`. A project role is not sufficient,
  because workforce pools are organization resources.

## Steps

Get the scripts:

```bash
BASE=https://raw.githubusercontent.com/tohweizhong/agentic-demos/main/ge_utils/ge_wif_scim_check
for f in 1_list_pools.sh 2_list_providers.sh 3_check_wif_scim.sh; do curl -sO "$BASE/$f"; done
chmod +x *.sh
```

| Step | Command | Result |
|---|---|---|
| 1 | `./1_list_pools.sh [ORG_ID]` | The workforce pools in the organization. If you do not give `ORG_ID` and you can see only one organization, the script uses it. |
| 2 | `./2_list_providers.sh POOL_ID` | The providers in the pool, with the OIDC issuer or SAML type. |
| 3 | `./3_check_wif_scim.sh POOL_ID [PROVIDER_ID]` | The SCIM tenants and the attribute mapping of each provider, and a short summary. If you do not give `PROVIDER_ID`, the script checks every provider in the pool. |

Each script takes an optional last argument, `LOCATION`. The default is `global`.
