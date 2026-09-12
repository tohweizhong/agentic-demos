# Agent Rules for agentic-demos

Repository-wide instructions for developers and AI coding assistants working in `agentic-demos`.

This repository holds self-contained demos and prototypes for ADK, A2A, MCP, and Gemini Enterprise.
Each top-level folder is one independent demo.

**Do not list the demo folders here.** [`README.md`](README.md) is the single source of truth for
what each folder contains. A second list would drift from it.

---

## 1. This is an external repository

The remote is `github.com/tohweizhong/agentic-demos`. Treat every file as publishable.

Never add:

*   Internal shortlinks (`go/...`), Buganizer links (`b/...` or `b.corp.google.com`), or any
    `*.corp.google.com` URL.
*   `google3/` source paths, internal design docs, or x20 paths (`x20web`, `/google/data/...`).
*   Customer names, tenant domains, real project IDs, or evaluation data.
*   Access tokens, service account keys, or `.env` contents. Use `.env.example` with placeholders.

If a demo needs internal context to make sense, describe the concept in plain terms instead of
linking to the internal document.

---

## 2. Strict demo self-containment

*   Each demo folder owns its dependencies. Give it its own `requirements.txt` or `pyproject.toml`
    and its own virtual environment.
*   **Never share a `venv/` across demo folders.**
*   A demo must run from a clean clone after following only its own `README.md`.
*   Do not add a shared top-level utility package. If two demos need the same helper, copy it. These
    are teaching examples, and a shared dependency makes each one harder to read in isolation.

---

## 3. Language choices

| Use case | Language |
|---|---|
| CLI tools, probers, synthetic monitoring, backend services | **Go**, standard library first |
| ADK agents, notebooks, ML and data science | **Python** |
| Web frontends | **TypeScript** |

Do not introduce FastAPI, Flask, or Django for a production-shaped backend. Use Go.
Container base image for compiled binaries: `gcr.io/distroless/static`.

---

## 4. Per-demo context files

Some demos carry their own context file. A nested file stacks on top of this one, so it should hold
only what is specific to that demo.

> [!IMPORTANT]
> **Two demos must keep the filename `GEMINI.md`, not `AGENTS.md`:**
> `organic-chem-agent/` and `agents_cli/hr-onboarding-agent/`.
>
> Their `agents-cli-manifest.yaml` declares `agent_guidance_filename: "GEMINI.md"`. Renaming the
> file breaks the agents-cli contract. Everything else in this repository uses `AGENTS.md`.

---

## 5. Git workflow

**Solo repository. Commit directly to `main`. Do not open a pull request.**

1.  Run `git pull` before committing.
2.  Check `.gitignore` covers new credential files, build outputs, and compiled binaries
    (for example `ge-prober/ge-prober`) before staging.
3.  Scan the diff for the items in section 1 before every commit.
4.  Stage explicit paths. Do not run `git add .` in a repository of 22 independent demos, because
    it sweeps in unrelated work from other folders.
5.  Push to `main`.

> [!NOTE]
> This overrides the generic `git-workflow` skill and the `sharepoint-research` convention. Both
> require a feature branch and a pull request. Those rules exist for shared repositories. This
> repository has one developer, so a branch adds a step and protects nothing.
