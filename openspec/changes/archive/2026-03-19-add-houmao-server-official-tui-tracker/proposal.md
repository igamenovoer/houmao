## Why

`houmao-server` currently has only a thin CAO-backed watch layer, while the real TUI parsing and lifecycle reduction logic still lives in runtime-local shadow monitors and demo-only monitor code. That leaves the server without an official always-on understanding of live tmux-backed agent sessions just as we want the server to replace more CAO-owned behavior.

The first server-owned replacement step is to make `houmao-server` the authoritative owner of TUI parsing and continuous live state tracking for known tmux-backed Houmao sessions. To do that cleanly, the parsing/state path must stop going through `cao-server`, stop relying on file-backed watch mirrors, and become an in-memory server-owned control-plane service.

## What Changes

- Promote `houmao-server` to the authoritative owner of continuous TUI parsing and live state tracking for known tmux-backed Houmao sessions.
- Implement direct tmux and process probing inside `houmao-server` so session watch workers determine tmux liveliness, TUI process up/down state, and captured pane content without routing parsing or state tracking through `cao-server`.
- Use the existing `houmao-server` registration bridge as the primary discovery seed for the sessions this server manages, enrich that seed with manifest-backed metadata, and verify it against live tmux liveness while keeping shared-registry records as compatibility evidence rather than primary watch authority.
- Reframe the supported parser stack as the official TUI parser used by `houmao-server` for supported interactive tools instead of treating that parser as a server-side "shadow" subsystem.
- Add a server-owned in-memory live state model that tracks Houmao-owned session identity, `terminal_id` compatibility aliases, transport state, TUI process state, parse status, parsed surface or parse/probe errors, derived operator state, stability timing, and bounded recent transitions for each watched session.
- Keep the existing terminal-keyed Houmao extension routes as the v1 external lookup surface, but resolve them through Houmao-owned tracked-session identity instead of making `terminal_id` the watch authority.
- Replace file-backed watch artifacts for this subsystem with in-memory authoritative state. Any later inspection routes should read server memory rather than claiming `current.json` or append-only watch logs as the truth surface.
- Keep CAO-compatible session-control routes as a separate concern. This change removes CAO from the parsing/state-tracking path first; it does not require eliminating the child CAO adapter from all other server routes in the same step.
- Supersede the current demo-scoped "shadow watch stability window" direction for live tracking by moving the state-tracking center of gravity into `houmao-server` and narrowing the overlapping change to demo-consumer behavior rather than competing tracker semantics.

## Capabilities

### New Capabilities
- `official-tui-state-tracking`: server-owned continuous in-memory tracking of known tmux-backed sessions, including tmux liveliness, TUI process liveliness, parsed TUI state, derived operator state, stability metadata, and bounded recent transitions

### Modified Capabilities
- `houmao-server`: replace CAO-polled/file-backed watch behavior with direct tmux/process observation and in-memory authoritative live state
- `versioned-shadow-parser-stack`: clarify how the existing parser core is used as the official supported TUI parser for `houmao-server` integrations and where legacy "shadow" terminology no longer applies at the server boundary

## Impact

- `src/houmao/server/service.py`, `src/houmao/server/models.py`, `src/houmao/server/app.py`, and `src/houmao/server/client.py`
- New server-owned TUI tracking modules under `src/houmao/server/`
- Shared tmux, parser, manifest, and compatibility-registry integration points under `src/houmao/agents/realm_controller/`
- Unit and integration coverage for tmux/process probing, official parser selection, and in-memory session tracking
- OpenSpec alignment between this change and the currently active `add-shadow-watch-state-stability-window` exploration, which should be narrowed to demo-only consumption or visualization rather than defining the primary server-owned live-tracking contract
