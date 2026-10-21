# WIF SCIM Tenant and Attribute Mapping Check

`check_wif_scim.sh` reads a Workforce Identity Federation (WIF) pool. For each provider in
the pool, it shows two facts:

1. If the provider has a SCIM tenant.
2. The attribute mapping of the provider. This tells you if `google.subject` keeps the case
   from the identity provider.

The script only reads. It does not change anything.

## Explanation

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

* The [Google Cloud CLI](https://cloud.google.com/sdk/docs/install). If `scim-tenants` is
  not found, run `gcloud components update`.
* Sign in with `gcloud auth login`.
* A role on the **organization** that can read workforce pool providers and list SCIM
  tenants, for example `roles/iam.workforcePoolAdmin`. A project role is not sufficient,
  because workforce pools are organization resources.

## Usage

```bash
chmod +x check_wif_scim.sh
./check_wif_scim.sh POOL_ID [PROVIDER_ID] [LOCATION]
```

If you do not give `PROVIDER_ID`, the script checks every provider in the pool. The default
`LOCATION` is `global`.
