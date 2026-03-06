## Why

CAO-backed demo scripts in `scripts/demo/` currently fail or skip for the wrong reasons even when fixture credential inputs are present. The most visible issue is CAO terminal startup failing with `Agent profile not found`, which is presently surfaced as `SKIP: missing credentials`, making troubleshooting and demo reliability harder.

## What Changes

- Align CAO demo runtime context by ensuring demo-launched CAO server home/profile-store and `start-session` profile install path refer to the same profile store.
- Standardize CAO lifecycle handling in CAO-backed session demos to use `python -m gig_agents.cao.tools.cao_server_launcher` (`status`/`start`/`stop`) as the sole server-management path.
- Tighten local loopback CAO startup behavior so untracked pre-existing local servers do not silently produce mismatched runtime context, and are handled via launcher-driven logic with explicit diagnostics.
- Improve demo skip classification so CAO profile-store mismatch errors are reported distinctly from genuinely missing credential inputs.
- Extend/clarify demo documentation for profile-store alignment and local CAO ownership expectations.

## Capabilities

### New Capabilities
- `cao-codex-demo-scripts`: define required behavior for CAO-backed Codex demo scripts, including profile-store alignment and explicit skip/fail taxonomy.

### Modified Capabilities
- `cao-claude-demo-scripts`: update Claude CAO demo requirements to require profile-store alignment with launcher context and explicit classification for profile-store mismatch errors.

## Impact

- Affected code: CAO-backed demo scripts under `scripts/demo/` for Claude and Codex, plus corresponding README guidance.
- Affected behavior: demo startup/skip/fail decision boundaries and operator-visible diagnostics.
- No runtime core API changes; this change focuses on demo-pack orchestration and specification coverage.
