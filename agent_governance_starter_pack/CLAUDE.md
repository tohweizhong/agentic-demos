# Claude Code Rules for Agent Governance Starter Pack

@AGENTS.md

## Claude Code Notes

1. Start `claude` from `agent_governance_starter_pack/`. The scripts and the Terraform paths are relative to this folder.
2. Use the `geap-*` skills in `.claude/skills/` for each workflow step. `.claude/skills` is a symlink to `.agents/skills`, so the Antigravity CLI and Claude Code use the same skill files.
3. `.claude/settings.json` holds the same allow, ask, and deny lists as `settings.json`. Never try to bypass an `ask` or a `deny` rule. Do not suggest `--dangerously-skip-permissions` or `bypassPermissions` mode.
4. In headless mode (`claude -p`), run read-only tasks only. If a step needs approval, stop and report the command that needs approval.
