# Product Guidelines: GEAP Starter Pack

## Writing

- Write all text in Simplified Technical English (ASD-STE100). This includes READMEs, runbooks,
  Terraform descriptions, policy file comments, code comments, log lines, and commit messages.
- Short sentences: 20 words or fewer for instructions, 25 for descriptions.
- Active voice. No contractions. No semicolons. One instruction in each sentence.
- Use the same word for the same thing every time. For example: "agent", "principal",
  "egress gateway", "MCP server", "policy", "mini build", "target design".
- Mark each claim that is not tested as "Not tested" or "Inference". Mark a tested claim with the
  test that proves it.

## Voice and tone

- Plain and factual. No marketing words.
- Explain the "why" in one sentence before a step.
- Say what the mini build does not cover. Do not let a reader think that a partial component is
  complete.

## Terraform

- Each Terraform variable and output has a `description` in STE.
- Placeholders only in `*.tfvars.example`. Real values go only in a gitignored `terraform.tfvars`.
- Pin the `google` provider version in each root module.
- Clean-up uses `terraform destroy` from the Terraform state. This is the main method.
- Labels are extra. Put the label `starter-pack = "mini-build"` only on resources that support
  labels. In provider 8.10.0, Agent Registry services, IAM access policies, and policy bindings do
  not support labels.
- Least privilege: grant on the resource, not on the project, when possible. Never grant
  `roles/iam.serviceAccountTokenCreator` at the project level.

## Policy files

- Keep each policy (IAP, Model Armor, org policy) in its own file, apart from the code. A security
  reviewer must be able to read it without the Terraform.
- Each policy file starts with a comment that states what the policy allows, what it denies, and
  its mode (`DRY_RUN` or enforce).
- A change from `DRY_RUN` to enforce is a separate commit with its own description.

## Runbooks

- Each runbook has these sections: Purpose, Before you start, Steps, Check the result, Restore.
- Number the steps. One action in each step.
- Each step that changes a cloud resource gives the command and the expected output.
- "Check the result" names the log or the console page where the reader sees the result. For
  example: the IAP Data Access audit log for a denied call.
- Times: local time with the zone, and UTC in brackets. Raw log data stays in UTC.

## Verification

- Verification follows the order in the product definition: identity, catalog, gateway control, audit.
- Every sample-only resource or step carries a visible "Sample only" label.
- The "switch policy mode" runbook returns the environment to its start state without a full redeploy.

## Public repository rules

- Placeholders only: no real project IDs, project numbers, org IDs, client IDs, agent IDs, tokens,
  or secrets.
- No internal links, internal paths, or customer names.
- Scan every change for secrets and for these items before a commit.
- Stage explicit paths. Do not run `git add .`.
- Work on the feature branch for this starter pack. Never force push.
