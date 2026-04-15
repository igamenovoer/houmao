# Houmao Docs

Houmao is a framework and CLI toolkit for building and running teams of CLI-based AI agents (`claude`, `codex`, `gemini`) as real tmux-backed processes — each with its own isolated disk state, native TUI, and gateway sidecar. This site covers the full reference, getting-started guides, and developer internals for installed users, with additional material for contributors.

| Who you are | Where to start |
|---|---|
| **Installed user** (`uv tool install houmao`) | Run `houmao-mgr system-skills install --tool claude`, start your agent, invoke the `houmao-touring` skill — or read [Easy Specialists](getting-started/easy-specialists.md) for the manual path |
| **From-source developer** (`pixi install && pixi shell`) | [Quickstart](getting-started/quickstart.md) — covers `agents join` and project-overlay build/launch with `pixi run` |
| **Contributor to Houmao** | [CLAUDE.md](https://github.com/igamenovoer/houmao/blob/main/CLAUDE.md) or [AGENTS.md](https://github.com/igamenovoer/houmao/blob/main/AGENTS.md) for repo conventions and development commands |

## Getting Started

- [Architecture Overview](getting-started/overview.md): Two-phase lifecycle, backend model, and high-level design.
- [Agent Definitions](getting-started/agent-definitions.md): Agent definition directory layout — tools, roles, recipes, launch profiles, and skills.
- [Quickstart](getting-started/quickstart.md): Build a brain and start your first session.
- [Easy Specialists](getting-started/easy-specialists.md): The easy lane — specialists, optional easy profiles, and instances.
- [Launch Profiles](getting-started/launch-profiles.md): Reusable birth-time launch configuration — easy profiles, explicit launch profiles, and the precedence chain.
- [Managed Agent Memory](getting-started/managed-memory-dirs.md): Per-agent memory roots, free-form memo files, and pages.
- [System Skills Overview](getting-started/system-skills-overview.md): Narrative tour of every packaged Houmao-owned system skill, when each one fires, and how managed-home auto-install differs from explicit CLI-default install.
- [Loop Authoring Guide](getting-started/loop-authoring.md): Choose between the three loop skills, understand the pairwise-v2 routing-packet prestart model, and discover the graph tooling that supports plan authoring.

## Reference

### CLI Surfaces

- [houmao-mgr](reference/cli/houmao-mgr.md): Primary management CLI for agents, brains, and server control.
- [houmao-server](reference/cli/houmao-server.md): HTTP server for session management and TUI tracking.
- [houmao-passive-server](reference/cli/houmao-passive-server.md): Registry-driven stateless server — no legacy dependencies.
- [houmao-mgr credentials](reference/cli/houmao-mgr.md#credentials-dedicated-credential-management): Dedicated top-level credential-management command family for Claude, Codex, and Gemini, with a matching `project credentials` wrapper.
- [system-skills](reference/cli/system-skills.md): Install and inspect packaged Houmao-owned skill sets for resolved tool homes.
- [agents gateway](reference/cli/agents-gateway.md): Gateway lifecycle and explicit live-gateway request commands.
- [agents turn](reference/cli/agents-turn.md): Managed headless turn submission and inspection.
- [agents mail](reference/cli/agents-mail.md): Managed-agent mailbox follow-up commands.
- [agents mailbox](reference/cli/agents-mailbox.md): Late filesystem mailbox registration for local managed agents.
- [admin cleanup](reference/cli/admin-cleanup.md): Registry and runtime maintenance commands.
- [internals graph](reference/cli/internals.md): NetworkX-backed graph helpers for loop plan authoring, structural analysis, and packet validation.
- [CLI Entrypoints](reference/cli.md): Module-level entry points and common runtime flags.

### Build Phase

- [Launch Overrides](reference/build-phase/launch-overrides.md): Override system for launch parameters.
- [Launch Policy](reference/build-phase/launch-policy.md): Policy engine for operator prompt modes and unattended execution.

### Run Phase

- [Launch Plan](reference/run-phase/launch-plan.md): Composing manifest + role into a backend-specific launch plan.
- [Session Lifecycle](reference/run-phase/session-lifecycle.md): Start, resume, prompt, and stop sessions.
- [Backends](reference/run-phase/backends.md): Backend model — local interactive, headless, and server-backed.
- [Role Injection](reference/run-phase/role-injection.md): Per-backend role injection strategies.
- [Managed Launch Prompt Header](reference/run-phase/managed-prompt-header.md): Houmao-owned prompt header with five independently controllable sections prepended to every managed launch by default — content, per-section control, composition, opt-out flags, and stored launch-profile policy.

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
- [Managed Agent API](reference/managed_agent_api.md): Direct agent control API surface.

## Developer Guides

- [TUI Parsing](developer/tui-parsing/index.md): Shadow parser architecture, signal contracts, and maintenance.
- [Terminal Recorder](developer/terminal-record/index.md): Recording internals and capture format.
- [Houmao Server Internals](developer/houmao-server/index.md): Server-owned TUI tracking and service orchestration.

## Resources

- [TUI State Tracking Resources](resources/tui-state-tracking/README.md)
