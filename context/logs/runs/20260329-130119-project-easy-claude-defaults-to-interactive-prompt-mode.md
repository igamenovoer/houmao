# Run Log: `project easy` Claude specialist generation omits unattended prompt mode for TUI launch

## Summary

During an interactive test of `houmao-mgr project easy`, creating a Claude specialist and launching it through `project easy instance launch` started Claude Code in interactive onboarding mode instead of unattended TUI mode. The underlying issue is not that `easy` chose the interactive backend instead of headless; Claude's launch-policy registry explicitly supports unattended `raw_launch` for TUI sessions. The `easy` specialist-generation path simply omitted `launch.prompt_mode: unattended` from the generated preset.

## Environment

- Date: 2026-03-29 UTC
- Repo: `/data1/huangzhe/code/houmao`
- Specialist: `python-sde`
- Tool: `claude`
- Credential lane: `kimi-coding`

## Commands

```bash
pixi run houmao-mgr project easy specialist create \
  --name python-sde \
  --tool claude \
  --credential kimi-coding \
  --system-prompt "You are a senior Python software engineer..." \
  --api-key "$ANTHROPIC_API_KEY" \
  --base-url "$ANTHROPIC_BASE_URL" \
  --claude-state-template-file tests/fixtures/agents/tools/claude/auth/kimi-coding/files/claude_state.template.json

pixi run houmao-mgr project easy instance launch \
  --specialist python-sde \
  --name python-sde \
  --yolo
```

## Observed Behavior

- The live tmux pane entered Claude Code's first-run onboarding/theme-selection TUI.
- The runtime manifest recorded:
  - `backend = "local_interactive"`
  - `launch_policy_request.operator_prompt_mode = "interactive"`
  - `launch_policy_provenance = null`
- The spawned command was plain interactive Claude:

```bash
claude --append-system-prompt 'You are a senior Python software engineer...'
```

## Root Cause

The generated easy preset omitted launch prompt mode entirely:

```yaml
skills: []
auth: kimi-coding
```

The `project easy specialist create` implementation hardcodes:

- `_write_role_preset(..., prompt_mode=None)` in `src/houmao/srv_ctrl/commands/project.py`

So the resulting preset does not carry `launch.prompt_mode: unattended`, and the later launch path passes `target.preset.operator_prompt_mode` through as `None`. In launch-policy application, `None` falls through to interactive mode.

## Why This Is A Bug

Claude TUI unattended launch is supported in the current source tree:

- `src/houmao/agents/launch_policy/registry/claude.yaml`
  - strategy `claude-unattended-2.1.81`
  - `operator_prompt_mode: unattended`
  - supports backend `raw_launch`

So the `easy` path is failing to express a supported launch mode, not hitting an inherent runtime limitation.

The surrounding UX reinforces the gap:

- `project easy specialist create --help` has no `--prompt-mode` option
- `project agents roles presets add` does have `--prompt-mode`
- checked-in Claude presets in `tests/fixtures/agents/roles/*/presets/claude/*.yaml` commonly use `launch.prompt_mode: unattended`

## Suggested Fix

One of:

1. Add `--prompt-mode` to `project easy specialist create` and persist it into the generated preset.
2. Default Claude and Codex `project easy specialist create` presets to `launch.prompt_mode: unattended` unless explicitly overridden.

Option 1 is safer, but the current default is surprising for operator workflows that expect no-prompt TUI startup.
