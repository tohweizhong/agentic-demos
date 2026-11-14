# OKF bundle to a Knowledge Catalog context set

This demo pushes a small Open Knowledge Format (OKF) bundle into a Knowledge Catalog
context set with the `kcmd` CLI. It then pulls the context set back, shows what an agent
receives, and loads a matching BigQuery table. Use it to fill Knowledge Catalog with test
data and then test the data in a Gemini Enterprise app.

All data in this demo is fictional. The project names, owners, and URLs are placeholders.

## Concepts

| Term | Meaning |
|---|---|
| OKF | [Open Knowledge Format](https://github.com/GoogleCloudPlatform/open-knowledge-format). A folder of Markdown files with YAML frontmatter. Each file is one concept. `index.md` describes the bundle. `_links.yaml` holds links between concepts. |
| Knowledge Catalog | The Google Cloud metadata catalog (formerly Dataplex Universal Catalog). Every cataloged asset is an entry in an entry group. |
| Context set | An entry group of type `context-set`. It holds curated documents that agents read as context. See [Context sets](https://docs.cloud.google.com/knowledge-catalog/docs/context-sets) and [Manage context sets](https://docs.cloud.google.com/knowledge-catalog/docs/manage-context-sets). |
| kcmd | The Knowledge Catalog Markdown CLI ([source](https://github.com/GoogleCloudPlatform/knowledge-catalog), npm package `@google-cloud/kcmd`). It runs `init`, `pull`, `push`, and `mcp`. |

## Folder content

| Path | Content |
|---|---|
| `bundle/` | The OKF bundle: `index.md`, five fictional project entries, and `_links.yaml`. |
| `seed/` | `projects.csv` and `schema.json` for the BigQuery table `projects`. One row for each entry. |
| `scripts/setup.sh` | Checks the tools, installs kcmd into `.tools/`, and enables the Dataplex and BigQuery APIs. |
| `scripts/push.sh` | Runs `kcmd init` in `workspace/`, copies `bundle/`, runs a dry run, and pushes. |
| `scripts/pull.sh` | Pulls the context set into `pulled/bundle/`. Tries again on the first-pull 403 error. |
| `scripts/lookup.sh` | Runs a context lookup on one entry and an entry search. |
| `scripts/seed_bigquery.sh` | Creates the BigQuery dataset and loads the `projects` table. |
| `scripts/cleanup.sh` | Deletes the entry links, the entries, the entry group, and the BigQuery dataset. Asks for confirmation. |
| `scripts/_env.sh` | Shared settings. The other scripts source it. |
| `.env.example` | Settings template. Copy it to `.env`. |

`.env`, `.tools/`, `workspace/`, and `pulled/` are local only. Git ignores them.

## Prerequisites

- A Google Cloud project with billing.
- Google Cloud CLI (`gcloud` and `bq`), signed in with `gcloud auth login`.
- Node.js 22.12 or later, with npm.
- IAM roles on the project:
  - `roles/dataplex.contentCreator` to create the context set and its entries.
  - `roles/dataplex.contentEditor` to update and delete them.
  - `roles/bigquery.dataEditor` and `roles/bigquery.jobUser` for the seed data.
  - `roles/serviceusage.serviceUsageAdmin` if the Dataplex or BigQuery API is not enabled yet.

## Quick start

1. Copy the settings file and set your project ID:

   ```bash
   cd okf_context_sets
   cp .env.example .env
   # Edit .env: set PROJECT_ID. Keep REGION=us-central1 or change it.
   ```

2. Check the tools, install kcmd, and enable the APIs:

   ```bash
   scripts/setup.sh
   ```

3. Push the bundle. kcmd creates the entry group `okf-demo-catalog` as a context set:

   ```bash
   scripts/push.sh
   ```

   Expected result: `Pushed 6/6 change(s) to okf-demo-catalog (6 create, 0 update, 0 delete).`

4. Pull the context set back and compare it with the source:

   ```bash
   scripts/pull.sh
   diff -ru bundle pulled/bundle
   ```

5. Show what an agent receives:

   ```bash
   scripts/lookup.sh                      # entry project-borealis, query "Borealis"
   scripts/lookup.sh project-tidewater    # another entry
   ```

6. Optional, for the Gemini Enterprise test: load the BigQuery table:

   ```bash
   scripts/seed_bigquery.sh
   ```

7. Test in a Gemini Enterprise app. See [Test in a Gemini Enterprise app](#test-in-a-gemini-enterprise-app).

8. When you are done, delete everything:

   ```bash
   scripts/cleanup.sh
   rm -r workspace pulled   # local kcmd workspaces for the deleted context set
   ```

To change the content, edit the files in `bundle/` and run `scripts/push.sh` again.

## OKF to Knowledge Catalog mapping

Observed with kcmd 0.2.5.

| OKF element | Knowledge Catalog result | Round trip (`kcmd pull`) |
|---|---|---|
| Frontmatter `type: Project Catalog Entry` | `document` aspect `data.type: project-catalog-entry` (slug). The entry type is always `document`. | Returns as `project-catalog-entry`. The human label is lost. |
| `title` | `entrySource.displayName` | Exact. |
| `description` | `entrySource.description` | Exact value. The YAML line wrap differs. |
| `resource` (URL) | `entrySource.resource` | Exact. |
| `tags` | No native field. Stored in an `## OKF Metadata` YAML block at the end of the `overview` aspect. | Exact value. A flow list becomes a block list. |
| `generated`, `verified`, `status`, `stale_after` (trust fields) | The same `## OKF Metadata` block in `overview`. No native field. No server-side effect. Deprecated and stale entries return as normal. | Exact. |
| Body Markdown | `overview` aspect, `contentType: MARKDOWN`. | Exact. |
| Body Markdown links `[x](y.md)` | Text only. kcmd does not make entry links from them. | Exact, as text. |
| `bundle/_links.yaml` | Entry links. `related` is undirected. `reference` is directed, from SOURCE to TARGET. | Same links. The file gets an `id` for each link and explicit SOURCE and TARGET roles. |
| Root `index.md` | Entry `agents` (document type `context-set`). Its `title` and `description` also set the entry group display name and description. `okf_version` goes to the `## OKF Metadata` block. | Returns as `agents.md`, not `index.md`. |
| `log.md` | Not pushed. kcmd skips `log.md` as a reserved OKF history file. | Lost. |
| (new on pull) | Each concept gets an `x-kcmd` block: entry type, location, `trailingNewline`, document aspect. | Added by kcmd. |

A context lookup returns the `resource`, `type: Document`, the `description`, the full
`overview` Markdown, and the document type. For an entry with links, it also returns
`relatedResources` with the linked entries. The trust fields reach the agent only as text
in the `## OKF Metadata` block. The agent must interpret `status: deprecated` and
`stale_after` itself.

## Known issues

| Issue | Workaround |
|---|---|
| kcmd reads the region from `gcloud config get-value compute/region`. If it is not set, kcmd fails with `Unable to retrieve project, location, or token`. | `scripts/_env.sh` sets `CLOUDSDK_CORE_PROJECT` and `CLOUDSDK_COMPUTE_REGION` from `.env`. |
| kcmd 0.2.5 on npm has no `status` command. The kcmd README describes a newer version. | Use `kcmd push --dry-run` to see pending changes. |
| The first read after a new push can fail with status 403 for about one minute, while IAM permissions propagate. Both `kcmd init` and `kcmd pull` read the context set. | `scripts/pull.sh` tries again up to six times, 20 seconds apart. In our test, the second attempt worked. |
| A context lookup in the first minute after a push can return `{}`. A new entry can take some minutes to appear in entry search. | Wait one or two minutes, then run `scripts/lookup.sh` again. |
| `log.md` is not pushed. | Keep the bundle history in Git. This demo does not include `log.md`. |
| Markdown links in the body stay as text. | Put each link in `_links.yaml`. Only `_links.yaml` (or frontmatter `links`) makes entry links. |
| Trust fields (`verified`, `status`, `stale_after`) stay as text in the `## OKF Metadata` block. | Tell the agent in its instructions how to treat `deprecated` and stale entries. |
| A push from a workspace without pull state reports updates for unchanged files, because the local format differs from the server format. | Run `scripts/pull.sh`, then edit and push from `pulled/` if you want a clean diff. |
| The entry links list method is not public. | `scripts/cleanup.sh` reads the link IDs from `pulled/bundle/_links.yaml`. Run `scripts/pull.sh` before cleanup. |

## Test in a Gemini Enterprise app

Gemini Enterprise uses Knowledge Catalog through a setting on the app, not through a data
store. The public guide is
[Connect Knowledge Catalog](https://docs.cloud.google.com/gemini/enterprise/docs/connectors/connect-knowledge-catalog).

Facts from the public guide:

- The setting is **Enable Knowledge Catalog** on the **Assistant** tab of the app
  configuration.
- Gemini Enterprise turns the setting on automatically when you attach a BigQuery, Cloud SQL,
  Spanner, or AlloyDB for PostgreSQL data store in federated query mode.
- The integration uses end-user credentials. For custom metadata such as a context set,
  users need view access in Knowledge Catalog, for example `roles/dataplex.catalogViewer`.

What we observed in our test:

- An app with only Google Drive data stores did not call Knowledge Catalog tools for a
  project or document question. This was true with the setting on, and also with a custom
  skill that told the assistant to use Knowledge Catalog.
- To test, attach a BigQuery data store in federated query mode and ask a data question.

Steps (console only, this demo does not change Gemini Enterprise):

1. Run `scripts/push.sh` and `scripts/seed_bigquery.sh`.
2. In the Google Cloud console, go to the **Gemini Enterprise** page.
3. Click **Data stores**, then create a **BigQuery** data store. Select
   **Federated query** mode. Follow the public BigQuery connector guide for the details.
4. Open your app. Click **Connected data stores** and add the new BigQuery data store.
5. Click **Configurations**, then select the **Assistant** tab. Make sure that
   **Enable Knowledge Catalog** is on. Click **Save and publish**.
6. Make sure that your test user has `roles/bigquery.dataViewer` on the dataset and
   `roles/dataplex.catalogViewer` on the project.
7. Ask the example questions below in the app.

Example questions:

- "Which projects in the okf_demo projects table are deprecated or stale, and who owns them?"
- "List the active projects tagged confidential, with the owner email for each."
- "Which projects are related to Project Borealis, and what is the status of each one?"

The first two questions need the BigQuery table. The third question needs the entry links
in the context set. Examine the agent trace in the app to see whether the assistant called
the Knowledge Catalog search and lookup tools.

## Cleanup

`scripts/cleanup.sh` asks you to type the entry group ID. It then deletes:

- The entry links (IDs from `pulled/bundle/_links.yaml`).
- All entries in the entry group.
- The entry group.
- The BigQuery dataset and its tables.

It does not delete Gemini Enterprise data stores or apps. Delete those in the console.

## References

- Open Knowledge Format: https://github.com/GoogleCloudPlatform/open-knowledge-format
- Knowledge Catalog tools and kcmd: https://github.com/GoogleCloudPlatform/knowledge-catalog
- kcmd on npm: https://www.npmjs.com/package/@google-cloud/kcmd
- Context sets: https://docs.cloud.google.com/knowledge-catalog/docs/context-sets
- Manage context sets: https://docs.cloud.google.com/knowledge-catalog/docs/manage-context-sets
- Connect Knowledge Catalog to Gemini Enterprise: https://docs.cloud.google.com/gemini/enterprise/docs/connectors/connect-knowledge-catalog
