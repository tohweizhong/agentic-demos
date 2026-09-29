# Project Notes: agy-im8-agent

Design decisions, known traps, and open questions for this codelab. Read this
before you change the lab. The commit history records what changed. This file
records why.

Last updated: 21 Sep 2026.

---

## 0. Quick start

```bash
cd agy-im8-agent
python3 init_im8_db.py     # rebuild im8_policies.db, which is generated and ignored
adk web                    # start the visual interface, then open localhost:8000
```

`sample_target_repo/` ships with all four defects in place. Restore them after a
demo with `git checkout -- sample_target_repo`.

### Open decisions

Two questions are unresolved. Both are written out in full below.

1. **Section 9a**: keep or drop SQLite and MCP. Three options, with the work
   each one needs. Option B is the recommendation.
2. **Section 10**: deploy to Agent Runtime and Gemini Enterprise. Four new steps
   are planned. One design question blocks the first of them.

### Two rules this project learned the hard way

1. A repair tool must prove the defect is gone. Read the file back. See section 5.
2. Never invent a control identifier. Cite the public catalog. See section 5a.

---

## 1. What this project is

A workshop lab for the Singapore Whole-of-Government CIO Workshop, Play 4:
Agent Creator with Antigravity 2.0.

The attendee prompts Antigravity 2.0 to build an autonomous IM8 compliance
companion. The companion audits a mock public sector repository, repairs the
defects, and writes a CIO attestation report.

The lab is modelled on the organic chemistry codelab in
[organic-chem-agent](../organic-chem-agent/). That lab sets the pattern: the
attendee only writes prompts and never copies code by hand.

---

## 2. History

The folder began life at `coding/scratchpad/codelab-agy-im8-agent`. It held a
single-agent implementation with a command line runner in `im8_agent/main.py`.

It moved to `coding/agentic-demos/agy-im8-agent` and the `codelab-` prefix was
dropped. The old `im8_agent/` package and `requirements.md` were deleted when
the multi-agent pipeline replaced them.

---

## 3. Current architecture

```
User prompt (ADK web chat)
        |
        v
SequentialAgent: im8_pipeline
        |
        +-- ParallelAgent: parallel_auditors
        |        |
        |        +-- code_security_specialist   -> as-8, lm-19
        |        +-- infra_security_specialist  -> as-13, ns-2
        |
        +-- cio_report_assembler -> IM8_COMPLIANCE_REPORT.md
```

Both specialists call the FastMCP policy server for the rule text. They call
their own audit tool to scan or repair.

| File | Role |
|---|---|
| `app/agent.py` | The pipeline. Exports `root_agent` and `app`. |
| `app/tools.py` | Audit tools, repair logic, report writer, clock tool. |
| `mcp_im8_server.py` | FastMCP stdio server. Three policy tools. |
| `init_im8_db.py` | Seeds `im8_policies.db` with four real controls. Run this first. Holds the attribution. |
| `sample_target_repo/` | The mock service with four planted defects. |
| `CODELAB.md` | The lab guide. Source of truth for the published codelab. |

---

## 4. Design decisions and the reasons

**Why a parallel multi-agent pipeline.** The single agent version worked, but it
taught nothing about orchestration. Code defects and infrastructure defects are
independent, so they are a natural fit for `ParallelAgent`.

**Why the Model Context Protocol.** The IM8 policy catalog is the correct thing
to put behind MCP. It separates government rules from agent code. An agency can
change a rule without a code change. The server holds the rule text, the
severity, and the approved repair template.

**Why the ADK web interface.** The attendee can watch both specialists run at
the same time in the trace panel. A terminal hides that.

**Why the run steps come after the launch step.** The first draft launched the
web interface at step 9, after the audit and the repair were already done. The
attendee opened the interface with nothing left to watch. The launch step now
comes first, at step 7.

---

## 5. Two real defects found by testing

Both were found by running the pipeline, not by reading the code. This is the
most useful lesson in this file.

**Defect 1: false remediation success.** `audit_infra_security` reported
`REMEDIATED` while the public access grant stayed in the Terraform file. The
pattern matched only `google_storage_bucket_iam_binding` with a `members` list.
The sample file uses `google_storage_bucket_iam_member` with a single `member`
field.

The fix has two parts. Match both resource styles. Then read every repaired file
back and test it against the defect pattern again. Report `REMEDIATION FAILED`
when the defect remains.

**Defect 2: invented dates.** The assembler agent wrote "2024-07-30" and
"October 26, 2023" into the attestation report. A model has no clock. The fix is
`get_assessment_timestamp`, which returns real Singapore time.

A third, smaller issue: the planted `# VIOLATION` and `# Non-compliant` comments
survived the repair. A compliant file carried a comment that said
"Non-compliant". `_strip_stale_markers` removes them.

---

## 5a. The control identifiers were invented, then fixed

The first version of this lab used `IM8-Sec-01`, `IM8-Data-02`, `IM8-App-04` and
`IM8-Infra-03`. None of those are real. I wrote them to make the demo readable.
The lab then presented them as Singapore Government policy on a public site.

The full Instruction Manual 8 is not public. It sits behind the government
portal and needs authorised credentials. Under the IM8 Reform programme,
GovTech does publish a control catalog for low-risk cloud systems, and that
catalog is open source.

* Repository: <https://github.com/GovTechSG/tech-standards>
* File: `catalogs/im8-reform.json`, version 2025.05.13
* Licence: MIT, Government Technology Agency of Singapore
* Format: OSCAL, the open control format from NIST
* Size: 137 controls in 16 groups

Profiles sit in `profiles/`, named `low-risk-level-{0,1,2}.json` and
`medium-risk-level-{0,1,2}.json`. Level 0 is a must-have, Level 1 a
should-have, Level 2 a good-to-have.

All four demo defects mapped cleanly onto real controls.

| Old invented ID | Real control | Why it fits |
|---|---|---|
| `IM8-Sec-01` | `as-8` Secrets Management | "Do not store secrets unencrypted in source code or configuration files." |
| `IM8-Data-02` | `lm-19` Log Sanitisation | "Sanitise logs... masking or tokenisation... not stored in plaintext." |
| `IM8-App-04` | `as-13` Exposure of Internal System Details | "without exposing internal system details such as debug information". |
| `IM8-Infra-03` | `ns-2` Access Restrictions on CSP Resources Outside Virtual Network | "Restrict access to S3 Buckets with IAM policies and block public access from the internet." |

Profile levels for low-risk cloud: `as-8` and `ns-2` are Level 1. `lm-19` and
`as-13` are Level 2. No control in the set is Level 0.

To re-derive the mapping, download the catalog and search the control prose. The
catalog is one JSON file of about 290 kB.

The agent instructions now carry an explicit order: quote the catalog and never
invent a control. A false citation in a compliance report is worse than no
report.

---

## 6. Environment traps

| Problem | Answer |
|---|---|
| `python3 -m venv` fails | `ensurepip` is absent. There is no working `.venv`. Use the user site packages. |
| `pip3 install` refused | The environment is externally managed. Add `--user --break-system-packages`. |
| `uv` | Not installed. |
| `mcp` version | `pip install mcp` pulls 2.x, where `FastMCP` was renamed to `MCPServer`. This code needs 1.x. Install `"mcp>=1.2.0,<2.0.0"`. Version 1.30.0 works. |
| Model | `gemini-2.5-flash`. The earlier draft named `gemini-3.7-flash`, which does not exist. |

---

## 7. How to verify the agent

Seed the database first. Then run the tools directly.

```bash
python3 init_im8_db.py

# Scan only.
python3 -c "
from app.tools import audit_code_security, audit_infra_security
print(audit_code_security('sample_target_repo', remediate=False))
print(audit_infra_security('sample_target_repo', remediate=False))
"

# Repair, then rescan. Every rule must report COMPLIANT.
python3 -c "
from app.tools import audit_code_security, audit_infra_security
print(audit_code_security('sample_target_repo', remediate=True))
print(audit_infra_security('sample_target_repo', remediate=True))
"

# Put the defects back.
git checkout -- sample_target_repo
```

To test the whole pipeline, write a short script that drives `root_agent` with
`InMemoryRunner` and prints every tool call. Keep it out of git.

Start the web interface from this folder, not from `app/`. The audit tools
resolve `sample_target_repo` against the working directory of the server.

```bash
adk web
```

---

## 8. Publishing

The lab guide lives in `CODELAB.md`. The published codelab is generated from it
by changing four metadata fields: the `id`, the `categories`, the `feedback
link`, and the `tags`. Lowercase tags avoid the keyword warnings. Keep
`categories` to `AI, Cloud`.

Validate every Mermaid diagram before you publish. A diagram that fails to
compile renders as a blank block.

---

## 9. Commit history

| Commit | Subject |
|---|---|
| `2575926` | Add agy-im8-agent parallel multi-agent IM8 compliance codelab |
| `ca8a813` | Fix false remediation success in the IM8 audit tools |
| `1c7ebe3` | Teach repair verification in the IM8 codelab |
| `b87feee` | Run the IM8 audit and repair inside the ADK web interface |
| `e3384c7` | Set Weizhong Toh as the codelab author |
| `b35e3ed` | Replace invented IM8 rule IDs with real public controls |

---

## 9a. Open decision: keep or drop SQLite and MCP

Not decided. Nothing has been changed.

### The question

Four controls fit in a Python dictionary. The SQLite layer stores four rows and
never queries across them. MCP starts a stdio subprocess. Both could go.

### The three options

| Option | What you keep | Cost |
|---|---|---|
| A. Remove both | One plain function tool holding four controls | The lab no longer teaches MCP. The workshop loses a stated learning goal. |
| B. Remove SQLite, keep MCP | An MCP server that reads the live public OSCAL catalog | Needs a network call, or a cached copy for an offline workshop machine. |
| C. Keep both | Current state | An extra build step and a database file that holds four rows. |

### The facts behind the trade-off

The SQLite layer earns very little. A dictionary does the same work.

MCP is the main blocker for deploying to Agent Runtime. See section 10. The
stdio server starts as a subprocess, so the script and its data must ship inside
the deployment package.

The case for MCP is still real. The public catalog holds 137 controls in 16
groups. GovTech maintains it and updates it on its own schedule. It is already
machine readable in OSCAL. That is a genuine reason to put it behind a tool
boundary rather than hardcode it.

### Recommendation on the table

Option B. Point the MCP server at the published catalog and drop the database.

* The lab drops from eleven steps to ten, because the seed step goes away.
* A contrived database is replaced by a real external source.
* For an offline workshop machine, the server downloads the catalog once and
  caches it to a local file.

### If option B is chosen, the work is

1. Delete `init_im8_db.py` and the `im8_policies.db` entry in `.gitignore`.
2. Change `mcp_im8_server.py` to fetch
   `https://raw.githubusercontent.com/GovTechSG/tech-standards/master/catalogs/im8-reform.json`,
   cache it locally, and parse the OSCAL tree for a control by identifier.
3. Keep the repair templates in the server file, clearly marked as lab examples.
4. Delete codelab step 3 and renumber the steps that follow.
5. Update the two diagrams in `README.md` and `CODELAB.md`.

### If option A is chosen, the work is

1. Move the four controls into `app/tools.py` as a dictionary.
2. Delete `mcp_im8_server.py` and `init_im8_db.py`.
3. Delete codelab steps 3 and 4, then renumber.
4. Remove the MCP learning goal from the overview.
5. Note that this also removes the Agent Runtime deployment blocker.

---

## 10. Next work: deploy to Agent Runtime and Gemini Enterprise

The plan is four more steps.

**The blocker.** The agent cannot deploy as it stands. Two parts assume a local
machine.

1. `mcp_im8_server.py` starts as a stdio subprocess at a path built from
   `__file__`. The script and `im8_policies.db` must ship inside the deployment
   package. `agent_engines.create` takes an `extra_packages` argument for this.
2. The audit tools read and write `sample_target_repo` on disk. A remote sandbox
   has no such folder. Any repair it writes is lost when the session ends.

**The four steps.**

| Step | Title | Duration |
|---|---|---|
| 10 | Prepare the Agent for Remote Deployment | 0:08:00 |
| 11 | Deploy to Vertex AI Agent Runtime | 0:08:00 |
| 12 | Register the Agent in a Gemini Enterprise App | 0:06:00 |
| 13 | Clean Up | 0:02:00 |

The current summary step moves from 11 to 14. Total length grows from about 45
minutes to about 70 minutes.

The notebook in [ae_ge_publish](../ae_ge_publish/) already holds working code
for steps 11 and 12. Lift the `agent_engines.create` call and the Discovery
Engine registration call from it.

**The open question.** Step 10 is the real work. Should the remote agent audit a
repository it clones from a Git URL, or audit file content supplied in the
prompt? This is not decided.
