## Why

Interactive testing of the new Houmao server pair exposed two contract holes in the main workspace. Pair-owned profile installation currently works only when a caller knows the internal child-CAO home path, and delegated launch still depends on raw untyped session JSON to recover tmux window identity.

## What Changes

- Add a pair-owned install path so `houmao-srv-ctrl install --port <public-port>` targets a specific running `houmao-server` instead of mutating whichever local `HOME` happens to be active.
- Add a `houmao-server` install surface for child-managed CAO profile state so callers no longer compute or depend on hidden `child_cao` filesystem paths.
- Add typed session-detail and session-terminal-summary parsing for `GET /sessions/{session_name}` and use that contract in `houmao-server` and `houmao-srv-ctrl`.
- Require delegated launch registration and runtime artifact materialization to preserve authoritative tmux window identity from the pair authority.
- Update pair docs and verification so the supported boundary stays `houmao-server + houmao-srv-ctrl`, not "demo code that reverse-engineers child storage."

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-cao-compat`: add pair-targeted install behavior and require delegated launch to preserve tmux window identity from typed session detail.
- `houmao-server`: add a server-owned install surface for child-managed CAO profile state and make session-detail compatibility responses explicit enough for typed pair clients.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/*`, `src/houmao/server/*`, `src/houmao/cao/models.py`, `src/houmao/cao/rest_client.py`, and pair-facing demo flows that currently compute child-home paths directly.
- Affected public surfaces: additive `houmao-srv-ctrl install --port`, additive `houmao-server` extension routes or commands for pair-owned install, and typed session-detail handling on existing compatibility routes.
- Verification: unit coverage for typed session detail and pair-targeted install, plus live validation that the dual shadow-watch demo no longer depends on internal child-path derivation.
