# Houmao Docs

Houmao is a framework and CLI toolkit for orchestrating teams of CLI-based agents as real tmux-backed processes.

> **New here?** Start with the [project README](https://github.com/igamenovoer/houmao#readme) for installation, quick-start workflows (`agents join`, easy specialists, recipe launch), and runnable demos. This site covers the full reference, developer guides, and subsystem internals.

## Getting Started

- [Architecture Overview](getting-started/overview.md): Two-phase lifecycle, backend model, and high-level design.
- [Agent Definitions](getting-started/agent-definitions.md): Agent definition directory layout — tools, roles, recipes, launch profiles, and skills.
- [Quickstart](getting-started/quickstart.md): Build a brain and start your first session.
- [Easy Specialists](getting-started/easy-specialists.md): The easy lane — specialists, optional easy profiles, and instances.
- [Launch Profiles](getting-started/launch-profiles.md): Reusable birth-time launch configuration — easy profiles, explicit launch profiles, and the precedence chain.
- [System Skills Overview](getting-started/system-skills-overview.md): Narrative tour of the eight packaged Houmao-owned system skills, when each one fires, and how managed-home auto-install differs from explicit CLI-default install.

## Reference

### CLI Surfaces

- [houmao-mgr](reference/cli/houmao-mgr.md): Primary management CLI for agents, brains, and server control.
- [houmao-server](reference/cli/houmao-server.md): HTTP server for session management and TUI tracking.
- [houmao-passive-server](reference/cli/houmao-passive-server.md): Registry-driven stateless server — no legacy dependencies.
- [CLI Entrypoints](reference/cli.md): Module-level entry points and common runtime flags.

### Build Phase

- [Launch Overrides](reference/build-phase/launch-overrides.md): Override system for launch parameters.
- [Launch Policy](reference/build-phase/launch-policy.md): Policy engine for operator prompt modes and unattended execution.

### Run Phase

- [Launch Plan](reference/run-phase/launch-plan.md): Composing manifest + role into a backend-specific launch plan.
- [Session Lifecycle](reference/run-phase/session-lifecycle.md): Start, resume, prompt, and stop sessions.
- [Backends](reference/run-phase/backends.md): Backend model — local interactive, headless, and server-backed.
- [Role Injection](reference/run-phase/role-injection.md): Per-backend role injection strategies.

### Subsystems

- [Gateway](reference/gateway/index.md): Per-agent FastAPI sidecar for session control and mail.
- [Mailbox](reference/mailbox/index.md): Unified mailbox protocol — filesystem and Stalwart JMAP.
- [TUI Tracking](reference/tui-tracking/state-model.md): State machine, detectors, and replay engine.
- [Lifecycle](reference/lifecycle/completion-detection.md): Turn-anchored readiness and completion detection.
- [Agent Registry](reference/registry/index.md): Session discovery and managed agent records.
- [Terminal Record](reference/terminal-record/index.md): tmux session recording and replay.
- [System Files](reference/system-files/index.md): Filesystem layout and owned paths.

### Other Reference

- [Claude Vendor Login Files](reference/claude-vendor-login-files.md): How to import Claude vendor login state, what each file means, and how to validate that lane locally.
- [Release Publishing](reference/release-publishing.md): PyPI trusted publishing setup and the public release flow.
- [Houmao Server Pair](reference/houmao_server_pair.md): Server + manager pair workflows.
- [Runtime-Managed Agents](reference/agents/index.md): Session model, targeting, and recovery.
- [Managed Agent API](reference/managed_agent_api.md): Direct agent control API surface.

## Developer Guides

- [TUI Parsing](developer/tui-parsing/index.md): Shadow parser architecture, signal contracts, and maintenance.
- [Terminal Recorder](developer/terminal-record/index.md): Recording internals and capture format.
- [Houmao Server Internals](developer/houmao-server/index.md): Server-owned TUI tracking and service orchestration.

## Resources

- [TUI State Tracking Resources](resources/tui-state-tracking/README.md)
