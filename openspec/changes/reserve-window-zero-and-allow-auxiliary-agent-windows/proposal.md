## Why

The repo currently treats the gateway sidecar as something that must stay out of the visible tmux session so it cannot interfere with raw TUI output. That restriction blocks a useful operator mode: keeping gateway, monitoring, or other support processes visible in their own tmux windows while preserving one stable agent surface.

## What Changes

- Relax the gateway visibility contract so supported tmux-backed sessions may host gateway or other support processes in auxiliary tmux windows instead of forcing every sidecar to remain a detached background process.
- Keep window `0` as the only contractual agent surface in same-session tmux layouts, and require auxiliary windows to remain non-authoritative for agent identity, attach guidance, and control targeting.
- Extend the tmux topology contract to cover both tmux-backed headless sessions and `cao_rest` sessions, while explicitly excluding `houmao_server_rest` from same-session sidecar windows.
- Keep the headless `agent` window-0 contract intact, but stop requiring auxiliary windows to stay backgrounded or hidden in order for runtime-controlled turns to keep using the primary agent surface.
- Define recovery and lifecycle behavior so gateway attach, detach, crash cleanup, or later agent relaunch do not destroy the reserved agent window `0`, and so relaunch in the same tmux session restores the agent process to window `0`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: change the gateway companion topology contract so supported tmux-backed sessions may expose gateway or monitoring output in auxiliary tmux windows while keeping the agent surface isolated.
- `brain-launch-runtime`: change the tmux session contract so supported same-session agent layouts reserve window `0` for the agent process, allow auxiliary windows to remain foreground for observability, exclude `houmao_server_rest` from that topology, and preserve or restore the agent surface on attach, detach, and relaunch.

## Impact

- Affected code includes gateway attach or detach launch paths, tmux helper primitives, headless runner window preparation, CAO session window-topology handling, and runtime recovery behavior.
- Affected observability surfaces include gateway logging, tmux attach expectations, and repo-owned helper flows that currently follow the session's active pane instead of an explicit agent surface.
- Affected documentation and tests include gateway lifecycle reference pages, runtime tmux topology guidance, CAO window-hygiene guidance, and integration or demo coverage for same-session auxiliary-window behavior.
