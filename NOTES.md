# Repository Notes: agentic-demos

Decisions and conventions for the repository as a whole. Each demo or codelab
folder may hold its own `NOTES.md` for decisions that apply only to that folder.

`README.md` lists what each folder holds. `AGENTS.md` states the repository
rules. This file records why the structure is the way it is.

Last updated: 30 Sep 2026 SGT.

---

## 1. The four codelabs

All four authored codelabs live under `codelabs/`. Each subfolder matches its
DevSite codelab identifier.

| Lab folder | DevSite ID | Authoring source | Images | Published state | Reference implementation |
|---|---|---|---|---|---|
| `codelabs/build-parallel-multi-agent-chemistry-assistant` | `build-parallel-multi-agent-chemistry-assistant` | `CODELAB.md` | `img/` | Live | Same folder, `app/` |
| `codelabs/adk-im8-compliance-agent-mcp` | `adk-im8-compliance-agent-mcp` | `CODELAB.md` | `img/` | Staged preview | Same folder, `app/` |
| `codelabs/adk-im8-compliance-agent` | `adk-im8-compliance-agent` | `CODELAB.md` | `img/` | Staged preview | Shares `adk-im8-compliance-agent-mcp/sample_target_repo/` |
| `codelabs/build-nus-transit-hub-antigravity` | `build-nus-transit-hub-antigravity` | `CODELAB.md` | `img/` | Live | Same folder, `app/` and `lib/` |

Find them with `ls codelabs/*/CODELAB.md`.

---

## 2. Three roles in each lab folder

The reference implementation is not the authoring source. It is the output of
the lab guide. If you cannot recreate `app/` by following `CODELAB.md`, the lab
is broken.

| Role | What it is | Who edits it | Tracked |
|---|---|---|---|
| Authoring source | `CODELAB.md`, `img/`, and `NOTES.md` | You, by hand | Yes |
| Reference implementation | The finished code the lab produces | Regenerated, then committed | Yes |
| Rehearsal run | A throwaway copy built by following the prompts in `rehearsals/` | Nobody. It is output. | No |

### Rules for `codelabs/<lab>/`

1. One source name everywhere: `CODELAB.md`.
2. Never commit `index.lab.md`. Generate it at publish time. Git ignores `codelabs/*/index.lab.md`.
3. One image folder name everywhere: `img/`.
4. Keep the reference implementation in the same `codelabs/<lab>/` folder.
5. Restore starter defects with Git (`git checkout -- sample_target_repo`).
6. Put dry-run workspaces in `codelabs/<lab>/rehearsals/`, which Git ignores. Open Antigravity inside the specific `rehearsals/<run>/` subfolder so the agent cannot read the reference `app/` in the parent directory.

---

## 3. Decided: keep codelabs in `agentic-demos/codelabs/`

The codelabs stay in this monorepo under `codelabs/` instead of a separate
repository.

- Keeping `CODELAB.md` and its reference implementation in one folder prevents
  drift between the guide and the code.
- Co-authors contribute via fork and pull request, while the maintainer commits
  directly to `main`.
