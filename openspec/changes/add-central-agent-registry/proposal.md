## Why

Cross-process agent discovery currently depends on local tmux session state or on callers knowing a shared runtime-root layout. That breaks down when different groups of agents run under different projects or different runtime roots, so the system needs one central per-user discovery layer that can answer "where is this agent?" without moving runtime-owned authority out of each session root.

## What Changes

- Add a runtime-managed shared agent registry rooted at `~/.houmao/registry` by default, with the effective home directory resolved via `platformdirs`-aware path handling rather than a hardcoded Linux home path.
- Allow controlled redirection of the shared-registry root through `AGENTSYS_GLOBAL_REGISTRY_DIR` for CI and similar test environments.
- Define a versioned secret-free registry record contract for live published agents under `live_agents/`, including discovery identity, lease metadata, runtime and gateway pointers, mailbox identity, and terminal-container hints.
- Make shared-registry agent-name input accept either `gpu` or `AGENTSYS-gpu`, while storing and resolving through one canonical reserved-prefix form internally.
- Update runtime-owned session lifecycle flows to publish, refresh, and remove registry records while keeping `manifest.json`, `gateway/attach.json`, and other session-root artifacts authoritative.
- Add stale-cleanup tooling for `live_agents/` directories left behind by unexpected failure.
- Add runtime resolution support for looking up agents through the shared registry when tmux-local discovery or a shared runtime root is unavailable.
- Document registry ownership, freshness rules, duplicate-name handling, and the boundary between shared discovery metadata and per-session runtime state.

## Capabilities

### New Capabilities
- `agent-discovery-registry`: Shared per-user registry contract and resolution rules for locating published agents across runtime roots.

### Modified Capabilities
- `brain-launch-runtime`: Runtime-managed sessions publish and maintain shared-registry discovery records alongside existing manifest, tmux, gateway, and mailbox state.

## Impact

- Affected code: runtime lifecycle orchestration, session manifest/gateway integration points, mailbox binding publication paths, and new registry storage/models/helpers.
- Affected systems: tmux-backed runtime sessions, gateway-capable sessions, mailbox-enabled sessions, and any future discovery-aware orchestration flows.
- Dependencies: no new external service dependency; the registry is filesystem-based under `~/.houmao/registry` by default, implementation should use the existing `platformdirs` dependency to resolve the user's home directory for that root, and CI can redirect the root through `AGENTSYS_GLOBAL_REGISTRY_DIR`.
