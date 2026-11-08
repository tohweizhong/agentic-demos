# Plan: Mini build of the GEAP starter pack

Each task ends with its checks and one commit. Mark a task `[x]` when its commit is done.

## Phase 1: Layout and sample MCP server (step 1, part of step 3)

- [x] Task 1.1: Create the folder layout, `.gitignore`, the starter pack README, and the
  `pipelines/` note.
- [x] Task 1.2: Sample MCP server in Go (test first).
  - [x] Write tests for the in-memory store and for the two tools through an in-memory transport.
  - [x] Write the store, the tools, and the HTTP server.
  - [x] Write `tool_spec.json` and a test that compares it with the tools that the server lists.
  - [x] Write the Dockerfile (distroless static).
  - [x] Check: `go vet ./...`, `go test -cover ./...` above 60 percent.

## Phase 2: Reference agent (part of step 5)

- [x] Task 2.1: ADK agent in Python (test first).
  - [x] Write tests for the ID token header provider and for the agent setup.
  - [x] Write `tools.py` (MCP toolset with an ID token for the invoker service account).
  - [x] Write `agent.py` and the Agent Runtime entry point.
  - [x] Check: `pytest --cov` above 60 percent.
- [x] Task 2.2: `scripts/package_agent.sh` builds a repeatable source archive.

## Phase 3: Terraform (steps 2 to 5)

- [x] Task 3.1: Providers, variables, outputs, and `terraform.tfvars.example`.
- [x] Task 3.2: Base setup: APIs, Data Access audit logs for IAP, regional log bucket and sink.
- [x] Task 3.3: Catalog: Artifact Registry, Cloud Build image, Cloud Run, invoker service
  account, Agent Registry MCP server and platform endpoints.
- [x] Task 3.4: Control: gateway, IAP extension V2, authz policy, access policy and binding,
  Model Armor. Policy files in `policies/`.
- [x] Task 3.5: Agent: Agent Runtime with Agent Identity, Sessions, and the gateway binding.
  Grants to the single agent principal.
- [x] Check for each task: `terraform fmt -check -recursive`, `terraform validate`.

## Phase 4: Operations (steps 6 and 7)

- [x] Task 4.1: Scripts: `ask_agent.sh`, `read_audit_log.sh`, `cleanup.sh`.
- [x] Task 4.2: Runbooks: `add_agent.md` and `reset_demo.md`. Demo script in the README.

## Phase 5: Cloud verification (needs approval)

- [~] Task 5.1: `terraform plan` in the approved project. Show the plan summary. Wait for approval.
  - [x] `terraform plan` has no error: 56 to add, 0 to change, 0 to destroy.
  - [ ] Approval of the plan summary.
- [ ] Task 5.2: `terraform apply`. Run the success criteria in product.md. Record the results.

## Notes

- Terraform tasks 3.1 to 3.5 are in one commit, because the files depend on each other and do not
  validate alone.
- Terraform has offline tests with mock providers (`terraform test`). They do not call Cloud Build.
- `project_number` is a variable, not a data source, so that `terraform plan` makes no API call
  before the APIs are on.
