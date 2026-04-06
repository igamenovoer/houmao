## Context

`houmao-mgr agents gateway ...` currently has two selector modes. Explicit mode accepts `--agent-id` or `--agent-name` and resolves through managed-agent discovery. Current-session mode runs inside the owning tmux session, infers that tmux session as the target, and resolves authority from `HOUMAO_MANIFEST_PATH` first with `HOUMAO_AGENT_ID` plus shared-registry fallback second.

That leaves an operator gap for attach and follow-up gateway commands launched from an ordinary shell outside tmux when the operator knows the tmux session name but not the managed-agent identity. The registry and runtime model already persist enough information to support this path: live registry records include `terminal.session_name`, manifest authority already records the owning tmux session, and current-session resolution already knows how to validate a manifest against a tmux session binding.

The change is cross-cutting because it touches gateway CLI selector parsing, local registry-backed discovery, manifest-authority validation, and operator documentation for both the CLI reference and gateway workflow guides.

## Goals / Non-Goals

**Goals:**

- Add a supported outside-tmux selector for `houmao-mgr agents gateway ...` based on tmux session name.
- Reuse existing manifest-first and shared-registry authority instead of introducing a parallel attach mechanism.
- Preserve current `--agent-id`, `--agent-name`, and `--current-session` behavior.
- Rename the gateway command family's pair-authority override from `--port` to `--pair-port` so it cannot be confused with the gateway listener port.
- Keep `--pair-port` semantics strict so tmux-session targeting follows the addressed session's persisted authority rather than an arbitrary server override.
- Make the new selector available consistently across gateway commands that already operate on one managed agent.

**Non-Goals:**

- Introduce new agent selector aliases such as `--target-agent-name` or `--target-agent-id`.
- Rename every `--port` flag across the wider `houmao-mgr` CLI surface in this change.
- Change server API routes or require pair-managed servers to understand tmux session names as first-class remote identifiers.
- Redesign gateway execution modes, manifest schema, or registry schema.
- Expand the change into broader non-gateway command targeting work outside the existing managed-agent discovery contracts.

## Decisions

### 1. Add exactly one new explicit selector: `--target-tmux-session`

The gateway CLI should add `--target-tmux-session <tmux-session-name>` and treat it as mutually exclusive with `--agent-id`, `--agent-name`, and `--current-session`.

This gives operators one clear outside-tmux path without duplicating the existing explicit managed-agent selectors. It also keeps the command grammar aligned with what the user actually knows in the recovery case: sometimes the tmux session name is visible while the managed-agent identity is not.

Alternative considered: add `--target-agent-name` and `--target-agent-id` for naming symmetry. Rejected because those would duplicate existing `--agent-name` and `--agent-id` behavior without adding capability.

### 2. Resolve tmux-session targeting through manifest-first local authority with registry fallback

`--target-tmux-session` should resolve by:

1. verifying the addressed tmux session exists on the local host,
2. reading `HOUMAO_MANIFEST_PATH` from that tmux session when available,
3. falling back to a fresh shared-registry record selected by `terminal.session_name` when the manifest pointer is missing or stale,
4. loading the manifest-derived authority, and
5. validating that the resolved manifest still belongs to the addressed tmux session.

This reuses the same trust model as current-session attach and avoids introducing cwd-based guesses or new gateway-specific state files. It also preserves the manifest as the durable attach authority while keeping the registry as a locator layer.

Alternative considered: resolve `--target-tmux-session` directly from tmux env only. Rejected because it would fail unnecessarily when the tmux-published manifest pointer is stale even though the registry already carries the fresh manifest locator.

### 3. Keep server APIs unchanged and treat tmux-session targeting as a local CLI resolution feature

After resolving one tmux session to a manifest-backed managed-agent target, the CLI should continue using existing attach execution paths:

- pair-managed `houmao_server_rest` targets call the existing managed-agent gateway attach route using manifest-derived pair authority, and
- local runtime-backed targets resume the existing controller path and call local attach directly.

This keeps tmux-session names out of the remote API contract and avoids teaching `houmao-server` or `houmao-passive-server` a new public selector type.

Alternative considered: add tmux-session selectors to server routes. Rejected because tmux session names are host-local authority hints, not stable cross-host API identities.

### 4. Reject `--port` for tmux-session targeting

The gateway CLI should rename its pair-authority override from `--port` to `--pair-port`.

This makes the user-facing contract align with what the flag actually does today: it selects the Houmao pair authority, not the live gateway listener port. That distinction matters even more once the gateway workflow also includes explicit tmux-session targeting while lower runtime layers already use names like `--gateway-port` for listener binding overrides.

Within the gateway command family, `--pair-port` should remain valid only with `--agent-id` or `--agent-name`. For `--target-tmux-session`, the CLI should reject `--pair-port` the same way it already rejects pair-authority overrides for `--current-session`.

Alternative considered: keep the user-facing name as `--port` and only clarify the help text. Rejected because the existing ambiguity is semantic, not merely textual; the flag name directly suggests the wrong layer of port.

Alternative considered: allow `--pair-port` with `--target-tmux-session` and use the tmux session only as a lookup hint. Rejected because it creates an ambiguous authority story and makes failures harder to diagnose.

### 5. Extend the full gateway command family, not only `attach`

The new selector should apply consistently anywhere `houmao-mgr agents gateway ...` already targets one managed agent through explicit selectors or current-session targeting: `attach`, `detach`, `status`, `prompt`, `interrupt`, `send-keys`, and the `mail-notifier` subgroup.

This avoids a split mental model where attach can target by tmux session but follow-up gateway operations cannot. The selector work belongs in the shared gateway-target resolver rather than being special-cased only for attach.

Alternative considered: implement `--target-tmux-session` only for `attach`. Rejected because operators commonly need status and direct gateway follow-up immediately after attach, and inconsistent selector support would feel arbitrary.

## Risks / Trade-offs

- [Risk] Tmux-session targeting can be ambiguous if stale or duplicate local state exists. → Mitigation: require exactly one fresh resolved record and fail closed with identity details when ambiguity remains.
- [Risk] The gateway CLI could drift from the broader registry-discovery selector contract. → Mitigation: update the registry-discovery and native CLI specs together and keep tmux-session resolution in shared helpers where practical.
- [Risk] Renaming `--port` inside only the gateway command family creates some short-term inconsistency with other `houmao-mgr` commands that still use `--port`. → Mitigation: document the distinction explicitly and keep the rename scoped to the command family where gateway-port confusion is real.
- [Risk] Operators may assume tmux-session names become remote API identities. → Mitigation: document clearly that tmux-session targeting is a local CLI resolution path that still resolves to existing managed-agent authority.
- [Risk] Expanding selector support across the gateway subgroup can miss one command surface. → Mitigation: cover all single-target gateway commands in unit tests and CLI reference updates.

## Migration Plan

No manifest or registry schema migration is required. Existing runtime and registry artifacts already carry the tmux session name and manifest locator needed for resolution.

Rollout is a CLI and docs update plus regression coverage. If the change must be rolled back, removing the new selector and reverting the `--pair-port` rename returns operators to the existing `--agent-id`, `--agent-name`, `--current-session`, and `--port` paths without requiring cleanup of persisted runtime state.

## Open Questions

None. The current design intentionally keeps tmux-session targeting local to the CLI and does not widen server-side managed-agent selectors.
