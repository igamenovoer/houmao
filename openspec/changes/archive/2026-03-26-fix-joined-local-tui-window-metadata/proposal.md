## Why

`houmao-mgr agents join` can successfully adopt an existing TUI session, but the first post-join local control path rewrites the manifest without the adopted tmux window name. After that rewrite, `agents state` and `agents show` probe the default `agent` window instead of the real adopted window, so joined TUI sessions appear broken immediately after a successful join.

## What Changes

- Preserve adopted tmux window metadata for joined `local_interactive` sessions across resume and manifest persistence.
- Ensure post-join local TUI tracking and managed-agent views continue to target the adopted window name instead of falling back to the launch-time `agent` default.
- Add regression coverage for the real failure sequence: successful TUI join followed by `state`/`show` on the joined agent.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: joined tmux-backed sessions must preserve adopted window metadata across resume and later manifest rewrites.
- `houmao-mgr-agents-join`: a successfully joined TUI must remain operable through later local `state` and `show` commands without losing its adopted window identity.

## Impact

- Affected code: joined-session manifest persistence, local interactive resume state, managed-agent local TUI tracking, and join regression tests.
- Affected operator surface: `houmao-mgr agents join`, `houmao-mgr agents state`, and `houmao-mgr agents show` for joined TUI sessions.
- No new dependencies or new public commands.
