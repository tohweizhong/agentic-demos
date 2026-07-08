# Gemini Enterprise License Distribution Utility Scripts

This folder contains a set of shell scripts to manage and distribute Google Cloud Gemini Enterprise licenses using the REST APIs (Discovery Engine API).

## Prerequisites

Before running the scripts:
1. Make sure you have the [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and authenticated.
2. Authenticate to gcloud using:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
3. Ensure you have the **Billing Account Administrator** role (`roles/billing.admin`) on the target Google Cloud Billing Account.
4. Ensure the **Discovery Engine API** (`discoveryengine.googleapis.com`) is enabled in the target projects.

## Setup Configuration

1. Copy the `env.sh.template` file to `env.sh`:
   ```bash
   cp env.sh.template env.sh
   ```
2. Open `env.sh` in a text editor and fill in the configuration variables:
   * **`BILLING_ACCOUNT_ID`**: Your Google Cloud billing account ID.
   * **`BILLING_ACCOUNT_LICENSE_CONFIG_ID`**: The license configuration ID of the subscription (retrieve this using `./get_subscription.sh`).
   * **`ENDPOINT_LOCATION`**: Multi-region for the API endpoint (e.g., `us`, `eu`, `global`).
   * **`LOCATION`**: Multi-region for data stores/license configurations (e.g., `us`, `eu`, `global`).
   * **`USER_PROJECT_NUMBER`**: The project number used for API quota/billing where you have the `Service Usage Consumer` role.
   * **`TARGET_PROJECT_ID`**: The target project ID where users are located.
   * **`TARGET_PROJECT_NUMBER`**: The project number of the target project.

## Scripts Usage

All scripts will automatically source the configuration variables in `env.sh`.

### 1. Retrieve Subscription Details
To check your active subscriptions, remaining seats, and get the `BILLING_ACCOUNT_LICENSE_CONFIG_ID`:
```bash
./get_subscription.sh
```

### 2. Distribute Licenses to a Project
To allocate a specific number of seats to a project:
```bash
./distribute_license.sh <license_count> [target_project_number] [location] [license_config_id]
```
* **`<license_count>`** (Required): Number of licenses to distribute.
* **`[target_project_number]`** (Optional): Fallback to `TARGET_PROJECT_NUMBER` in `env.sh`.
* **`[location]`** (Optional): Fallback to `LOCATION` in `env.sh`.
* **`[license_config_id]`** (Optional): Specify this if you are updating an existing configuration. If omitted, a new project-level config will be created.

### 3. Reclaim Licenses from a Project
To retract licenses from a project back to the billing account pool (Note: this operation is limited to once per calendar day):
```bash
./reclaim_license.sh <license_count> <license_config_id> [target_project_number] [location]
```
* **`<license_count>`** (Required): Number of licenses to reclaim.
* **`<license_config_id>`** (Required): The license config ID of the project-level allocation (can be found in `./get_subscription.sh` output under `licenseConfigDistributions`).

### 4. Assign Licenses to Users
To manually assign seats/licenses to specific users:
```bash
./assign_user_license.sh <license_config_id_or_subscription_id> <user_email_1> [user_email_2] ...
```
* **`<license_config_id_or_subscription_id>`** (Required): The license config or subscription ID.
* **`<user_email_1> ...`** (Required): One or more user email addresses to assign.

### 5. List Assigned User Licenses
To list all users assigned to licenses in the target project:
```bash
./list_user_licenses.sh [target_project_id] [location]
```

### 6. Remove Licenses from Users
To unassign licenses from specific users:
```bash
./remove_user_license.sh <user_email_1> [user_email_2] ...
```
* **`<user_email_1> ...`** (Required): One or more user email addresses to remove from the license.
