# Connector-Level IAM for a Custom MCP Connector in Classic Gemini Enterprise

This folder holds a repeatable test. The test shows how to limit one Custom MCP connector to a
group of users in classic Gemini Enterprise. It contains a small MCP server in Go, the setup
scripts, and the results of a test on 17 Nov 2026.

## Contents

1. [Answer](#1-answer)
2. [Guidance: limit a Custom MCP connector to one group in an existing app](#2-guidance-limit-a-custom-mcp-connector-to-one-group-in-an-existing-app)
3. [Results](#3-results)
4. [Effect on existing connectors](#4-effect-on-existing-connectors)
5. [Steps](#5-steps)
6. [Lessons](#6-lessons)
7. [Limits](#7-limits)
8. [Sources](#8-sources)

## 1. Answer

**With the predefined role `roles/discoveryengine.agentspaceRestrictedUser` at project level, the
resource access control toggle hides nothing.** The user still sees and uses every connector.

**A Custom MCP connector is hidden when all of these conditions are true:**

- The resource access control toggle is on for the location.
- The user holds a custom project role with only two permissions:
  `discoveryengine.devToolsConfigs.get` and `discoveryengine.locations.buildAuthorizationUrl`.
- The user holds `roles/discoveryengine.agentspaceUser` on the app and on each connector that the
  user must see. The user has no grant on the Custom MCP connector.

When the user gets `agentspaceUser` on the Custom MCP connector, the connector comes back.

The predefined restricted role gives read access to all data stores and collections in the
project. So the resource-level check always passes, and the toggle has no effect.

## 2. Guidance: limit a Custom MCP connector to one group in an existing app

This section is for this situation:

- Classic Gemini Enterprise, with one shared app that has many existing connectors.
- All end users hold `roles/discoveryengine.agentspaceRestrictedUser` at project level, and
  `roles/discoveryengine.agentspaceUser` on the app.
- One new Custom MCP connector must be visible to one Google group only.
- A second app is not wanted, because two apps are hard to maintain.

Each statement has a tag. **[Tested]** means that the 17 Nov 2026 test showed it.
**[Documented]** means that the public documentation states it. **[Inference]** means that it
follows from the test and the documentation, but the test did not show it directly.

### 2.1 Does the toggle affect the other connectors?

- **[Tested]** With the predefined restricted role, the toggle changes nothing for any user. The
  toggle also does not hide the Custom MCP connector.
- **[Tested]** The change that affects connectors is the project role swap. After the swap to the
  custom role, a user sees only the connectors that have a grant for that user.
- **[Inference]** So after the swap, every user loses every connector that has no grant for the
  user. The test showed this for one user and one connector. It did not test a large app.

### 2.2 Safe order of steps

The order is important. Give all grants first. Swap the project role last.

| Step | Action | Effect for users |
|---|---|---|
| a | List every app and every connector in the location. The toggle applies to all apps and data stores in one location of the project. Use Google groups, not single users. | None |
| b | Do this test in a separate project first, with the scripts in this folder. | None |
| c | Create the custom role `customRestrictedEndUser` with the two permissions in [section 1](#1-answer). | None |
| d | Give `agentspaceUser` to the all-users group on the app and on every existing connector. For a connector with entities, give the role on the collection and on every entity data store. | None |
| e | Give `agentspaceUser` on the Custom MCP connector to the restricted group only. Give it on the collection and on its `_mcp_data` data store. | None |
| f | Turn on the toggle. The predefined role is still in place, so nothing changes yet. | None **[Tested]** |
| g | Swap the project role of the all-users group from `agentspaceRestrictedUser` to `customRestrictedEndUser`. This step takes effect. | The Custom MCP connector is hidden for non-members after about 5 minutes **[Tested for one user, not for a group]** |
| h | Check with one member and one non-member of the restricted group. Tell users to refresh the web app page. | None |
| i | Rollback: swap the project role back to `agentspaceRestrictedUser`. | Expected to restore access to all connectors **[Inference, not timed]** |

> [!NOTE]
> The test gave roles to one user directly. Grants to Google groups are expected to work the same
> way, because IAM treats group membership as a member of the binding. **[Inference]**

### 2.3 Things that cancel the control

The control does not hide a connector from a user who holds one of these roles at project level.
This applies to a direct grant and to a grant to a group that the user is in.

- [ ] Any predefined Discovery Engine role, for example `agentspaceRestrictedUser`,
  `agentspaceUser`, or `agentspaceAdmin`.
- [ ] Owner (`roles/owner`).
- [ ] Editor (`roles/editor`).

Admins keep full access, because they hold one of these roles. **[Documented]** The test showed
this for `agentspaceRestrictedUser` only. **[Tested]**

### 2.4 Reminders

- Enable the MCP tools after setup. Open the data store, then **Actions** > **Reload custom
  actions**, then enable each tool. The API does not do this. **[Tested]**
- Refresh the web app page after a change. An open page can show an old connector list.
  **[Tested]**
- The managed organization policy constraint
  `discoveryengine.managed.disableCustomMcpServerConnector` can block Custom MCP connectors.
  Check it before you start. **[Tested]**

## 3. Results

Test on 17 Nov 2026, classic Gemini Enterprise, location `global`. The test user had no other
roles in the project. Connector A is a Custom MCP connector. Its tool returns `MCP-MARKER-A`.
Connector B is a Cloud Storage data store. Its files hold `DOC-MARKER-B`.

| Round | Project role of the test user | Resource grants | Toggle | Connector A | Connector B |
|---|---|---|---|---|---|
| Baseline | `agentspaceRestrictedUser` | App | Off | Visible, tool called | Visible |
| 1 | `agentspaceRestrictedUser` | App | On | **No change.** Visible, tool called | Visible |
| 2 | `customRestrictedEndUser` | App, connector B | On | **Hidden** in about 5 minutes. Tool not called. | Visible |
| 3 | `customRestrictedEndUser` | App, connector B, connector A | On | **Back** in about 1 minute after the grant. Tool called. | Visible |

Evidence for each round:

- The answer text in the web app (the marker text or no marker).
- The Cloud Run log line `TOOL_CALL get_marker` for each tool call. In round 2, the log had no
  entries after the role swap.
- The connector menu in a new chat after a page refresh. In round 2, only connector B was listed.

Round 1 was checked 16 minutes after the toggle change. Round 2 changed only the project role, and
it took effect. So the toggle was active in round 1, and the predefined role caused the result.

## 4. Effect on existing connectors

- After the role swap, a user loses every connector that has no grant for that user. Plan the
  grants for all existing connectors before the swap. See [section 2.2](#22-safe-order-of-steps).
- Project-level predefined Discovery Engine roles, Owner, and Editor cancel the control. A user
  with one of these roles sees all connectors.
- The toggle applies to all apps and data stores in one location of the project.

## 5. Steps

### 5.1 Requirements

- A Google Cloud project with classic Gemini Enterprise (`experienceState` = `LEGACY_ONLY`).
- An admin account with Owner, or with the Discovery Engine admin, IAM admin, Cloud Run admin,
  and Storage admin roles.
- A test user with a Gemini Enterprise license and no project-level roles.
- `gcloud`, `curl`, `jq`, and `bash`. Go 1.25 or later to build the MCP server locally.

### 5.2 Configure

```bash
cp .env.example .env
# Edit .env. Set PROJECT_ID, PROJECT_NUMBER, TEST_USER, and BUCKET.
gcloud auth login
```

### 5.3 Run

Run the scripts in this order. Each script prints what it did.

| Step | Script | Action |
|---|---|---|
| 1 | `./00_preflight.sh` | Read-only checks: `experienceState`, toggle, organization policies, project roles of the test user. |
| 2 | `./10_deploy_mcp_server.sh` | Deploy the MCP server to Cloud Run. Print the `/mcp` URL. |
| 3 | `./20_create_docs_datastore.sh` | Create connector B and import two files. |
| 4 | `./30_create_mcp_connector.sh` | Create connector A with `setUpDataConnectorV2`. Then do the manual step that the script prints. |
| 5 | `./40_create_app.sh` | Create the app with both data stores. Print the web app URL. |
| 6 | `./60_round1_grants.sh` | Give the test user `agentspaceRestrictedUser` (project) and `agentspaceUser` (app). |
| 7 | Web app, as the test user | Baseline: ask for the connector A marker and the connector B marker. Expect both. |
| 8 | `./50_toggle.sh on` | Turn on the toggle. |
| 9 | Web app, as the test user | Round 1: refresh the page, open a new chat, ask again. Expect both markers. |
| 10 | `./70_round2_grants.sh` | Create the custom role, swap the project role, grant connector B only. |
| 11 | Web app, as the test user | Round 2, after about 5 minutes: refresh, new chat, ask again. Expect `DOC-MARKER-B` only. |
| 12 | `./80_grant_connector_a.sh` | Grant connector A (collection and data store). |
| 13 | Web app, as the test user | Round 3, after about 1 minute: refresh, new chat, ask again. Expect both markers. |
| 14 | `./99_cleanup.sh` | Remove all test resources and grants. |

Example questions for the web app:

- "What is the connector A marker? Use the MCP tool."
- "What is the connector B marker?"

Check the tool calls in the Cloud Run logs:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND textPayload:"TOOL_CALL get_marker"' \
  --project="$PROJECT_ID" --freshness=1h --format='value(timestamp,textPayload)'
```

### 5.4 Test the MCP server locally

```bash
cd mcp_server
go build -o iamtest-mcp .
PORT=8080 ./iamtest-mcp &

H=(-H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
curl -s "${H[@]}" localhost:8080/mcp -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
curl -s "${H[@]}" localhost:8080/mcp -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
curl -s "${H[@]}" localhost:8080/mcp -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_marker","arguments":{}}}'
```

The last call returns `MCP-MARKER-A`. The server is stateless, so no session header is necessary.

### 5.5 Files

| File | Purpose |
|---|---|
| `lib.sh` | Shared functions: `.env`, access token, REST calls, IAM read-modify-write that keeps existing bindings. |
| `mcp_server/main.go` | MCP server with one tool, `get_marker`. Streamable HTTP at `/mcp`. |
| `mcp_server/Dockerfile` | Multi-stage build. Final image `gcr.io/distroless/static`. |
| `.env.example` | Settings with placeholder values. |

## 6. Lessons

- **Custom MCP actions are off by default.** After an API setup, open the data store, click
  **Reload custom actions**, and enable each tool. Until then, Gemini Enterprise does not call the
  MCP server. The `PATCH` on `actionConfig` sets `actionState` to `ACTIVE`, but it does not enable
  a tool.
- **Create the app with all data stores in one call.** An app that was created with one data
  store cannot get more data stores later. The API returns `FAILED_PRECONDITION`.
- **Refresh the web app page after a change.** An open page can show an old connector list. A new
  chat after a refresh shows the correct list.
- **Check the organization policy first.** The managed constraint
  `discoveryengine.managed.disableCustomMcpServerConnector` can block the creation of a Custom MCP
  connector.
- **Python MCP servers:** version 2 of the `mcp` Python SDK removed the `mcp.server.fastmcp`
  module. If you write the server in Python, pin `mcp<2` or use the new API.

## 7. Limits

- The test covers classic Gemini Enterprise only. It does not cover the new Gemini Enterprise
  experience.
- The test ran on 17 Nov 2026 in the `global` location. The behaviour can change.
- The test used one test user with direct grants. It did not test Google groups.
- The test did not time the rollback.

## 8. Sources

- [Configure access controls for apps and data stores](https://docs.cloud.google.com/gemini/enterprise/docs/iam-policy-for-apps-and-data-stores)
- [Configure access controls for apps](https://docs.cloud.google.com/gemini/enterprise/docs/iam-policy-for-apps)
- [Set up a custom MCP server connector](https://docs.cloud.google.com/gemini/enterprise/docs/connectors/custom-mcp-server/set-up-custom-mcp-server)
- [Method: projects.locations.setUpDataConnectorV2](https://docs.cloud.google.com/gemini/enterprise/docs/reference/rest/v1alpha/projects.locations/setUpDataConnectorV2)
- [Configure allowed data sources](https://docs.cloud.google.com/gemini/enterprise/docs/connectors/configure-allowed-data-sources)
- [Go MCP SDK](https://github.com/modelcontextprotocol/go-sdk)
