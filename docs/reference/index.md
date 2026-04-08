# Runtime Reference

## CLI Surfaces

- [houmao-mgr](cli/houmao-mgr.md): Primary management CLI for agents, brains, and server control.
- [system-skills](cli/system-skills.md): Install and inspect the packaged Houmao-owned skill sets for resolved tool homes.
- [houmao-server](cli/houmao-server.md): HTTP server for session management and TUI tracking.
- [houmao-passive-server](cli/houmao-passive-server.md): Registry-driven stateless server.
- [CLI Entrypoints](cli.md): Module-level entry points and common runtime flags.

### Managed-Agent Command Families

- [agents gateway](cli/agents-gateway.md): Gateway lifecycle and explicit live-gateway request commands.
- [agents turn](cli/agents-turn.md): Managed headless turn submission and inspection.
- [agents mail](cli/agents-mail.md): Managed-agent mailbox follow-up commands.
- [agents mailbox](cli/agents-mailbox.md): Late filesystem mailbox registration for local managed agents.
- [admin cleanup](cli/admin-cleanup.md): Registry and runtime maintenance commands.

## Build Phase

- [Launch Overrides](build-phase/launch-overrides.md): Override system for launch parameters.
- [Launch Policy](build-phase/launch-policy.md): Policy engine for operator prompt modes and unattended execution.

## Run Phase

- [Launch Plan](run-phase/launch-plan.md): Composing manifest + role into a backend-specific plan.
- [Session Lifecycle](run-phase/session-lifecycle.md): Start, resume, prompt, and stop sessions.
- [Backends](run-phase/backends.md): Backend model and per-backend notes.
- [Role Injection](run-phase/role-injection.md): Per-backend role injection strategies.
- [Managed Launch Prompt Header](run-phase/managed-prompt-header.md): Houmao-owned prompt header prepended to every managed launch by default — content, composition order, opt-out flags, and stored launch-profile policy.

## Subsystems

- [Gateway](gateway/index.md): Per-agent FastAPI sidecar for session control and mail.
- [Mailbox](mailbox/index.md): Unified mailbox protocol — filesystem and Stalwart JMAP.
- [TUI Tracking State Model](tui-tracking/state-model.md): Tracked state, signals, and transitions.
- [TUI Tracking Detectors](tui-tracking/detectors.md): Detector profiles and registry.
- [TUI Tracking Replay](tui-tracking/replay.md): State reducer and replay engine.
- [Completion Detection](lifecycle/completion-detection.md): Turn-anchored readiness and completion pipelines.
- [Agent Registry](registry/index.md): Session discovery and managed agent records.
- [Terminal Record](terminal-record/index.md): tmux session recording and replay.
- [System Files](system-files/index.md): Filesystem layout and owned paths.

## Other Reference

- [Claude Vendor Login Files](claude-vendor-login-files.md): How Houmao imports `.credentials.json` and `.claude.json`, and how to validate that lane locally.
- [Release Publishing](release-publishing.md): PyPI trusted publishing setup and the GitHub release flow.
- [Realm Controller](realm_controller.md): Runtime session orchestration.
- [Houmao Server Pair](houmao_server_pair.md): Server + manager pair workflows.
- [Managed-Agent API](managed_agent_api.md): Direct agent control API surface.

- [Realm Controller Send-Keys](realm_controller_send_keys.md): Raw tmux send-keys control.
- [Houmao Server Agent API Live Suite](houmao_server_agent_api_live_suite.md): Server agent API validation.

## Developer Guides

- [TUI Parsing](../developer/tui-parsing/index.md): Shadow parser architecture and maintenance.
- [Terminal Recorder](../developer/terminal-record/index.md): Recording internals.
- [Houmao Server Internals](../developer/houmao-server/index.md): Server-owned TUI tracking.
