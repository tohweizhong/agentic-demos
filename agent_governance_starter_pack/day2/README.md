# Day-2 pack

> [!IMPORTANT]
> Status: plan only. No tool is built yet.

The Day-2 pack is a set of tools for a platform team that runs the agent governance starter pack
every week. Agents are added and removed. Tools and policies change. The Day-2 pack helps the team
keep the controls correct during these changes.

The starter pack [GUIDE.md](../GUIDE.md) covers Day 0 and Day 1: build the platform and hand it
over. The Day-2 pack covers the weeks after the handover.

## Why the Day-2 pack is a subfolder

- It reads the same Terraform state, the same Terraform outputs, and the same `name_prefix`.
- Its scripts reuse [`scripts/_common.sh`](../scripts/_common.sh).
- Its skills go in the existing [`.agents/skills/`](../.agents/skills/) folder. The same
  [`AGENTS.md`](../AGENTS.md) safety rules apply.
- It has the same version as the starter pack.
- The plan for each tool is a backlog item in the one conductor product
  ([`conductor/product.md`](../conductor/product.md#backlog)). There is no second product.

## Planned tools

| Tool | Question that the tool answers | Backlog item | Status |
|---|---|---|---|
| Posture check | Does each live agent have its gateway bindings, IAM grants, and IAP rules? Do IAM grants remain for agents that are deleted? | [#12](../conductor/product.md#backlog) | Not built |
| Promotion readiness | Which agent principals and tools will the IAP policy block when the mode changes from `DRY_RUN` to `ENFORCE`? | [#13](../conductor/product.md#backlog) | Not built |
| Agent onboarding | What Terraform block, IAM grants, and `DRY_RUN` IAP rule does a new agent need? | [#14](../conductor/product.md#backlog) | Not built |
| Tool policy check | Does each MCP tool that is not read-only have an explicit rule in the IAP access policy? | [#15](../conductor/product.md#backlog) | Not built |
| Emergency quarantine | How do I stop one agent now, without a change to the shared gateways or to other agents? | [#16](../conductor/product.md#backlog) | Not built |
| Principal access boundary for agents | Which resources can the agents of one project get access to, whatever their IAM grants are? | [#24](../conductor/product.md#backlog) | Not built. Not tested |
| Governance dashboard | How many calls did Model Armor block, which gateway status codes occur, and what is the MCP server latency? | [#21](../conductor/product.md#backlog) | Not built |
| CI checks | Does a pull request pass format, validation, tests, and the tool policy check? | [#19](../conductor/product.md#backlog) | Not built |
| Remote Terraform state | Is the Terraform state in a versioned bucket that the whole team can use? | [#20](../conductor/product.md#backlog) | Not built |

### Principal access boundary for agents

This tool is new. It is not in the backlog items 11 to 23. It is backlog item #24.

- The principal set for all agent identities in one project is
  `//agents.global.org-ORGANIZATION_ID.system.id.goog/attribute.container/projects/PROJECT_NUMBER`.
- The plan is to bind a principal access boundary policy to this principal set.
- To create a principal access boundary policy, you need the role
  `roles/iam.principalAccessBoundaryAdmin` on the organization. Thus an organization administrator
  creates the policy. Source:
  [Create and apply principal access boundary policies](https://docs.cloud.google.com/iam/docs/principal-access-boundary-policies-create),
  checked on 09 Nov 2026.
- The binding to the agent identities principal set of one project is a project-level binding.
- The starter pack [`AGENTS.md`](../AGENTS.md) does not allow organization-level changes. Thus a
  person must create the policy. The Day-2 tool can only make the project-level binding, after
  approval.
- Not tested. The behavior with Agent Identity and the egress Agent Gateway is not checked.

## Backlog items that stay in the starter pack

| Backlog item | Reason |
|---|---|
| #11 Claude Code harness | It is already built as part of the starter pack harness |
| #17 Multi-harness skill installer | It installs the starter pack skills on Day 0, not on Day 2 |
| #18 Model Armor config in YAML | It changes the starter pack Terraform, not a Day-2 tool |
| #22 Multi-agent least-privilege example | It is a policy example for the starter pack reference build |
| #23 Handover checklist | Handover is the last step of Day 1 |

## Design rules for the future tools

1. Each tool is read-only by default. It reports what it finds and changes nothing.
2. A change needs a flag and the approval of a person. Use the same pattern as
   `scripts/cleanup.sh --include-project-wide` ([runbooks/teardown.md](../runbooks/teardown.md)).
3. Each script sources [`scripts/_common.sh`](../scripts/_common.sh) and reads values from the
   Terraform outputs.
4. Each tool has one skill in [`.agents/skills/`](../.agents/skills/). The `AGENTS.md` safety rules
   and the `settings.json` permission lists apply to each skill.
5. This repository is public. Use placeholders only, for example `PROJECT_ID`, `PROJECT_NUMBER`,
   and `ORGANIZATION_ID`. Do not write real IDs, names, or internal links.
