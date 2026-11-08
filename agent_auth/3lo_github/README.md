# 3LO GitHub demo: Agent Identity and Auth Manager

An ADK agent on Agent Runtime reads GitHub with the token of the signed-in
user. The agent holds no GitHub secret.

- The agent uses its **Agent Identity** to call Auth Manager.
- **Auth Manager** runs the 3-legged OAuth (3LO) consent flow with GitHub and
  stores the user token in its vault.
- The agent uses the GitHub MCP server (`https://api.githubcopilot.com/mcp/`)
  in read-only mode.
- The [sample UI client](../client/) runs on Cloud Run behind Identity-Aware
  Proxy (IAP). It relays the consent request and finalizes the credential.

## Folder contents

| Path | Holds |
|---|---|
| `agent/agent.py` | The agent. The Gemini model client always uses the `global` location. |
| `agent/tools.py` | GitHub MCP toolset with the Auth Manager 3LO auth scheme. |
| `agent/.agent_engine_config.json` | Tells Agent Runtime to give the agent an Agent Identity. |
| `deploy/01_auth_provider.sh` | Enables APIs. Creates the GitHub auth provider if it does not exist. |
| `deploy/02_deploy_agent.sh` | Deploys the agent with `adk deploy agent_engine`. |
| `deploy/03_iam_grants.sh` | Grants the IAM roles to the agent and to the client service account. |
| `deploy/04_deploy_client.sh` | Makes the build service account. Deploys the client to Cloud Run with IAP. |
| `cleanup.sh` | Deletes only the resources that `.env` names. |
| `.env.example` | Placeholder settings. Copy it to `.env`. |

## Requirements

- A Google Cloud project with billing, in an organization. IAP for Cloud Run
  and Agent Identity need an organization.
- `gcloud` version 586.0.0 or newer, signed in with
  `gcloud auth login` and `gcloud auth application-default login`.
- Python 3.10 to 3.13.
- A GitHub account.

## Deploy

1. Make the settings file and the virtual environment.

   ```bash
   cp .env.example .env
   # Edit .env. Replace each YOUR_* value.
   python3 -m venv .venv
   .venv/bin/pip install uv
   .venv/bin/uv pip install --python .venv/bin/python -r agent/requirements.txt
   ```

   The `gcp` extra has many dependencies. `uv` resolves them much faster than
   `pip`. A plain `pip install -r agent/requirements.txt` also works, but it
   can take a long time.

2. Make the auth provider.

   ```bash
   ./deploy/01_auth_provider.sh
   ```

   If the script creates a new provider, register a GitHub OAuth app at
   GitHub **Settings > Developer settings > OAuth Apps**. Use the redirect URL
   that the script prints as the **Authorization callback URL**. Put the client
   ID and secret in `.env`, then run the script again.

3. Deploy the agent. The script writes the new `AGENT_ID` to `.env`.

   ```bash
   ./deploy/02_deploy_agent.sh
   ```

   The agent gets `OAUTH_CONTINUE_URI` before the client exists. The value is
   `https://CLIENT_SERVICE-PROJECT_NUMBER.REGION.run.app/validateUserId`,
   because Cloud Run service URLs have this fixed format.

4. Grant the IAM roles.

   ```bash
   ./deploy/03_iam_grants.sh
   ```

5. Deploy the client with IAP.

   ```bash
   ./deploy/04_deploy_client.sh
   ```

## IAM roles

| Principal | Role | Resource | Why |
|---|---|---|---|
| Agent Identity (`principal://agents.global.org-...`) | `roles/agentidentity.user` | Auth provider | The agent gets the user token from the vault. |
| Client service account | `roles/aiplatform.user` | Project | The client creates sessions and queries the agent. |
| Client service account | `roles/agentidentity.user` | Auth provider | The client calls `credentials:finalize`. |
| Build service account | `roles/cloudbuild.builds.builder` | Project | Cloud Build builds the client image. |
| IAP service agent | `roles/run.invoker` | Cloud Run service | IAP forwards requests to the client. |
| `IAP_MEMBER` | `roles/iap.httpsResourceAccessor` | Cloud Run service | The person can open the client. |

### Build service account

`gcloud run deploy --source` uses Cloud Build to make the client image. By
default, Cloud Build uses the default compute service account. In many
projects that account has no build role. `04_deploy_client.sh` makes a
dedicated build account (`BUILD_SA_NAME`) with only the Cloud Build builder
role, and gives it to `--build-service-account`. The script does not change the
default compute service account.

## Test the 3LO flow

1. Open the client URL that `04_deploy_client.sh` prints. Sign in through IAP.
2. In **Configuration Settings**, keep **Agent Type** as the remote agent.
   Enter the project ID and `us-central1`, then click **Load Remote Agents**.
3. Select `agent-auth-3lo-github` and click **Save & Apply Settings**.
   If you leave the fields empty, the client uses the agent in its environment.
4. Send this message: `List my last three updated repos`.
5. A popup opens on the GitHub consent page. Click **Authorize**.
6. The popup closes. The agent answers with your repositories, including
   private repositories.

To see the consent page again, revoke the OAuth app in GitHub
**Settings > Applications > Authorized OAuth Apps**. Auth Manager can keep a
token for the fixed user ID `default_user_id` from an earlier test.

## Known limits

- The client uses one fixed user ID. Keep the client behind IAP.
- A new IAM binding on the auth provider can take some minutes to apply.
  Before that, the agent logs a 403 error on
  `agentidentity.authProviders.retrieveCredentials`. Wait five minutes after
  `03_iam_grants.sh`, then test.
- The first answer after consent can take one to two minutes. If the reply is
  empty, send the message again.
- The GitHub auth provider supports one scope (`repo`).

## Clean up

```bash
./cleanup.sh
```

The script does not delete the auth provider unless
`AUTH_PROVIDER_OWNED_BY_DEMO=true` in `.env`.
