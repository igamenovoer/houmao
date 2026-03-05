## Why

CAO-managed Claude Code is now usable via tmux “shadow parsing”, but we do not have an end-to-end demo that proves two important real-world behaviors:

- Claude can actually write simple code artifacts onto disk under `tmp/<subdir>/...` (not just return text).
- A user can interrupt mid-turn (e.g. by pressing `Esc` in the tmux session) and the session can still accept a new prompt afterward.

These scenarios are exactly where tmux/TUI drift and runtime assumptions tend to break, so we want a repeatable demo to validate them (and to debug regressions using CAO’s terminal pipe logs).

## What Changes

- Add a new demo pack `scripts/demo/cao-claude-tmp-write/` that:
  - starts a CAO-backed Claude Code runtime session,
  - prompts Claude to create a small, deterministic code file under a unique `tmp/<subdir>/...`,
  - verifies the file exists and runs successfully (sentinel output),
  - records a sanitized `report.json` and supports `--snapshot-report`.
- Add a new demo pack `scripts/demo/cao-claude-esc-interrupt/` that:
  - starts a CAO-backed Claude Code runtime session,
  - submits a “long-ish” prompt, detects `processing`, then sends an `Esc` keystroke via tmux to interrupt,
  - verifies the terminal returns to an idle prompt,
  - sends a second prompt and verifies a non-empty response is extracted,
  - records a sanitized `report.json` and supports `--snapshot-report`.

Non-goals:

- Changing the CAO server API or provider implementations.
- Changing the Claude Code shadow parser logic (this change is about demos/validation).

## Capabilities

### New Capabilities

- `cao-claude-demo-scripts`: Provide reproducible demo packs that validate CAO-managed Claude Code filesystem writes and mid-turn interrupt recovery, including clear SKIP behavior and debug breadcrumbs (terminal id + log paths).

### Modified Capabilities

- (none)

## Impact

- `scripts/demo/...`: new demo directories, prompts, verifiers, and run scripts.
- `tmp/`: demo workspaces are created under `tmp/` (ignored by git).
- Developer workflow: provides a standard “smoke test” to run after Claude Code / CAO updates to confirm the tmux/TUI interaction surface still works.

