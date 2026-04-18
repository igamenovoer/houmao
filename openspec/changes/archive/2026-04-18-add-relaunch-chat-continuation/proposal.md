## Why

Provider CLIs now expose native startup flags for continuing an existing chat session, but Houmao relaunch always restarts the provider surface as a fresh chat. Operators need relaunch to recover or restart a managed TUI/headless surface while preserving provider conversation continuity when requested, especially after provider-side transient failures where the local tmux session remains the managed runtime authority.

## What Changes

- Add a relaunch chat-session selector to `houmao-mgr agents relaunch` with explicit fresh/default, provider-latest, and exact provider-session modes.
- Teach TUI relaunch to translate that selector into provider-native startup continuation args for Codex, Claude Code, and Gemini CLI.
- Teach native headless relaunch to persist the requested relaunch selector so the next managed headless prompt starts with the requested provider chat session.
- Add a launch-profile relaunch policy field so future live instances created from a profile can carry an operator-owned default relaunch chat-session behavior without changing first-launch behavior.
- Preserve current fresh-chat relaunch behavior by default and keep unsupported or invalid selector combinations explicit.
- Update lifecycle skill and docs guidance so agents and operators know when to choose fresh relaunch versus provider-native continuation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Runtime relaunch accepts and applies a provider-native chat-session continuation selector for TUI and headless managed sessions.
- `houmao-srv-ctrl-native-cli`: `houmao-mgr agents relaunch` exposes the relaunch chat-session selector and validation behavior.
- `agent-launch-profiles`: launch profiles can store a relaunch-only chat-session policy that applies to future managed instances created from the profile.
- `houmao-manage-agent-instance-skill`: managed-agent lifecycle guidance covers relaunch chat continuation and does not confuse it with a fresh launch.
- `docs-cli-reference`: CLI reference documents the new relaunch selector flags and examples.
- `docs-run-phase-reference`: run-phase lifecycle/backends documentation explains provider-native chat continuation during relaunch.

## Impact

- Affected runtime code: relaunch command handling, runtime controller relaunch plumbing, local interactive backend launch command construction, headless relaunch/startup-default handling, launch-profile catalog and manifest projection.
- Affected provider mappings: Codex uses `resume --last` / `resume <id>`, Claude uses `--continue` / `--resume <id>`, and Gemini uses `--resume latest` / `--resume <id>`.
- Affected tests: CLI option parsing, launch-profile persistence/resolution, TUI command construction, headless next-prompt startup selection, and relaunch validation.
- Affected docs/skills: managed-agent instance lifecycle skill, CLI reference, launch-profile guide, and run-phase lifecycle/backend reference.
