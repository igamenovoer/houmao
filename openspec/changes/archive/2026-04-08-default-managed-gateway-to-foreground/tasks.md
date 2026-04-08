## 1. Flip the managed attach CLI contract

- [x] 1.1 Update `houmao-mgr agents gateway attach` option parsing, help text, and managed-agent attach helpers so foreground same-session execution is the default and `--background` is the explicit detached-execution override.
- [x] 1.2 Extend the pair-managed gateway attach client/server request path to carry an optional execution-mode selection instead of hard-coding attach with no request body.
- [x] 1.3 Update `houmao-mgr project easy instance launch` to accept the new per-launch background override and to pass the resolved gateway execution mode into launch-time auto-attach.

## 2. Thread execution mode through runtime attach and reporting

- [x] 2.1 Update runtime gateway attach and auto-attach plumbing so tmux-backed managed sessions resolve foreground by default, preserve detached behavior only for explicit background requests, and keep tmux window `0` reserved for the agent surface.
- [x] 2.2 Update launch/attach/status payload construction so successful foreground attach surfaces include `execution_mode` and the authoritative `gateway_tmux_window_index`.
- [x] 2.3 Update curated gateway plain/fancy renderers and any related launch output helpers so the default foreground topology is visible in human-oriented output.

## 3. Refresh docs and skill guidance

- [x] 3.1 Update operator docs under `docs/reference/cli.md`, `docs/reference/cli/agents-gateway.md`, and `docs/reference/gateway/operations/lifecycle.md` to describe foreground-by-default attach and the new background overrides.
- [x] 3.2 Update gateway-related system skill guidance that currently instructs agents to use `--foreground` so it reflects the new default and opt-out behavior.

## 4. Verify foreground and background behavior

- [x] 4.1 Add or update unit tests for CLI option parsing, managed attach helper behavior, pair attach request payloads, and gateway status rendering of execution-mode metadata.
- [x] 4.2 Add or update tmux-backed integration coverage for default `agents gateway attach`, explicit `--background`, default easy-launch auto-attach, and easy-launch background override behavior.
- [x] 4.3 Run targeted Pixi-based tests and at least one live tmux repro to confirm the gateway runs in a non-zero auxiliary window by default and stays detached only when background mode is explicitly requested.
