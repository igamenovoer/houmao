---
name: houmao-launch-agents
description: 'Manual invocation only; use only when the user explicitly requests `houmao-launch-agents` by exact name or asks to use this specific skill. Launch maintained Claude Code or Codex workflows through the current fixture lanes: `tests/fixtures/plain-agent-def/`, `tests/fixtures/auth-bundles/`, and maintained demo-owned agent trees.'
---

# Houmao Launch Agents

The older overloaded shared fixture root is removed. Do not use archived `brains/`, `blueprints/`, or `api-creds` instructions from older notes.

Use one of these maintained launch patterns instead:

- `scripts/demo/minimal-agent-launch/` for a small end-to-end maintained launch demo.
- `scripts/demo/shared-tui-tracking-demo-pack/` for maintained live-watch or recorded TUI tracking workflows.
- `tests/fixtures/plain-agent-def/` plus `tests/fixtures/auth-bundles/` when you explicitly need a plain direct-dir experiment or credential CRUD target.

Read [references/command-cookbook.md](references/command-cookbook.md) for current commands.

## Supported Guidance

### Minimal maintained demo

Use the maintained minimal demo when you want one supported launch path with generated overlay-local state:

- `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code`
- `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex`

### Maintained TUI tracking demo

Use the maintained shared TUI tracking pack when you need live watch or recorder-backed evidence:

- `scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool claude`
- `scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool codex`

### Plain direct-dir experiments

Use `tests/fixtures/plain-agent-def/` only as a secret-free source tree. If a run needs auth inside its own direct-dir tree:

1. copy `tests/fixtures/plain-agent-def/` into a temp root,
2. materialize the selected bundle from `tests/fixtures/auth-bundles/<tool>/<bundle>/`,
3. point `--agent-def-dir` or `HOUMAO_AGENT_DEF_DIR` at that temp root.

### Credential management

For maintained credential CRUD:

- project-local flows: `pixi run houmao-mgr project credentials <tool> ...`
- plain direct-dir flows: `pixi run houmao-mgr credentials <tool> ... --agent-def-dir <path>`

Use a copied temp root or `tests/fixtures/plain-agent-def/` as the direct-dir example target.

## Guardrails

- Do not restore or commit historical `brains/api-creds` trees.
- Do not treat archived `scripts/demo/legacy/` packs as supported launch surfaces.
- When a workflow needs local credentials, source them from `tests/fixtures/auth-bundles/` and materialize them into the workflow-owned tree.
