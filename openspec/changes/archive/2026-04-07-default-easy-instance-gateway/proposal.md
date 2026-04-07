## Why

`houmao-mgr project easy instance launch` is the maintained specialist launch path, but it still makes operators attach the agent gateway as a separate follow-up step even though the gateway is the useful default for mailbox, prompt-routing, and live control workflows. That split adds friction to the common case and leaves new easy-launch sessions in a less useful posture than users usually want.

## What Changes

- Change `houmao-mgr project easy instance launch` so it requests launch-time gateway attach by default for supported easy instances.
- Default easy launch to loopback gateway binding with a system-assigned port when the caller does not explicitly request a port.
- Add an easy-launch opt-out flag, `--no-gateway`, so operators can skip launch-time gateway attach when they want a bare session.
- Add an easy-launch port override flag so operators can request a fixed gateway listener port for that launch.
- Surface the resolved gateway endpoint, or a degraded-success attach error, in the easy launch result so operators can immediately inspect or retry gateway work.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: `project easy instance launch` changes from "gateway-capable but detached by default" to "gateway auto-attached by default with explicit opt-out and port override behavior."

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/srv_ctrl/commands/agents/core.py`, and the delegated local launch/runtime plumbing they call.
- Affected CLI surface: `houmao-mgr project easy instance launch`.
- Affected tests: easy-instance launch CLI coverage, launch completion rendering, and gateway auto-attach success and degraded-success cases.
- Affected docs: easy specialist and CLI reference pages that describe `project easy instance launch`.
