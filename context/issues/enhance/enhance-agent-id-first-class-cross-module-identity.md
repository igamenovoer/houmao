# Enhancement Proposal: `agent_id` Should Become a First-Class Cross-Module Identity Contract

## Status
Proposed

## Summary
Houmao currently treats canonical agent name as the main identity surface across runtime control, tmux naming, shared-registry publication, mailbox defaults, and demo/operator state.

That is workable when the system assumes name alone is enough, but the new directory-layout work is introducing a stronger distinction:
- canonical agent name is the strong human-facing live identity,
- `agent_id` is the authoritative globally unique identity for system-owned writable association.

That change is wider than directory layout alone. If Houmao adds `agent_id` only in one place, the rest of the system will keep making name-only assumptions and the resulting contracts will drift.

This enhancement proposes the follow-up needed to make `agent_id` a real system contract rather than an isolated field.

## Why
Today several important surfaces are still name-centric:
- runtime start/control and tmux-backed lookup use `--agent-identity` and canonical `AGENTSYS-...` names,
- shared-registry layout and docs still assume name-derived directory keys and name-based resolution,
- mailbox defaults treat canonical agent identity as the default participant principal,
- demo persisted state and reports record `agent_identity` only,
- many tests, docs, and specs assume canonical agent name is the only durable agent identifier.

That becomes risky once Houmao starts relying on `agent_id` for writable ownership:
- same-name should usually mean same-agent, but rare real name conflicts still exist,
- rename or relabel flows should not silently become “new unrelated agent” by accident,
- same-id different-name situations should warn consistently across runtime, registry, and mailbox-related state,
- name-based lookup should stay convenient for operators without losing globally unique durable association.

In short, `agent_id` needs to be adopted deliberately across the main identity-bearing modules, not just added to one schema or one directory path.

## Requested Enhancement
### 1. Add a shared identity model for `canonical_agent_name` plus `agent_id`
Introduce one shared runtime-level identity contract that carries at minimum:
- `canonical_agent_name`
- `agent_id`
- whether the `agent_id` was explicitly supplied or default-derived
- any warnings produced by suspicious identity combinations

Default behavior should remain:
- canonical name is the operator-facing identity,
- default `agent_id` is `md5(canonical_agent_name)` in full lowercase hex,
- same `agent_id` with a different canonical name emits a warning and still treats `agent_id` as authoritative.

This should live in one shared helper or model layer rather than being reimplemented independently in runtime, registry, and mailbox code.

### 2. Persist both identity layers in runtime-owned artifacts
Runtime-owned artifacts should stop persisting only `agent_identity` and should instead carry both:
- canonical agent name for operator-facing continuity,
- authoritative `agent_id` for durable ownership and correlation.

This should apply at minimum to:
- start-session result payloads,
- session manifests,
- runtime-owned session-root metadata,
- any gateway or attach metadata that needs to correlate a live session with durable runtime state,
- any future job-dir metadata file if one is introduced.

The runtime should continue to use canonical agent name for tmux session naming and default CLI control targeting.

### 3. Add a registry contract that supports both name lookup and id-keyed ownership
If shared-registry writable ownership moves to `live_agents/<agent_id>/`, the registry also needs an explicit answer for name-based resolution.

This enhancement should require one of:
- a name-to-`agent_id` sidecar index, or
- another explicit secret-free lookup contract that avoids full-directory scans for the common “find agent by name” path.

The registry record contract should persist both canonical agent name and `agent_id`, and registry refresh or cleanup flows should warn on same-id different-name inconsistencies.

### 4. Define how CLI and control flows interact with `agent_id`
Normal operator-facing control should remain name- or manifest-based for now.

This enhancement should decide whether Houmao also needs:
- an explicit `--agent-id` input for start/build flows,
- an inspection or debugging surface that can show `agent_id`,
- a rule for validating name-to-id consistency during resume/control when both are available.

The default user experience should not force humans to type raw `agent_id` values for routine use.

### 5. Extend mailbox ownership metadata without replacing human-facing mailbox names
Mailbox is a separate subsystem, but it still has durable ownership and conflict semantics.

This enhancement should define whether mailbox registration state needs to persist:
- `owner_agent_id`,
- or equivalent agent-owned correlation metadata,
in addition to the current human-facing principal/address contracts.

This should not require replacing mailbox addresses or default `principal_id` with raw `agent_id`.
The goal is durable ownership and better conflict diagnostics, not making mailbox UX less readable.

### 6. Update demo, tutorial, and operator-state artifacts
Demo and operator flows currently persist `agent_identity` only. Those state files and reports should record both canonical agent name and `agent_id` so they can:
- distinguish “same live name, same logical agent” from suspicious reuse,
- survive future rename or relabel flows more cleanly,
- report clearer diagnostics when stale state or cleanup targets no longer match expected identity.

### 7. Refresh docs, specs, and tests as one coherent contract update
This enhancement should be treated as a contract update across runtime, registry, mailbox, and demo guidance rather than as a narrow implementation tweak.

Docs and tests should explain:
- what canonical agent name is for,
- what `agent_id` is for,
- when default `agent_id` derivation is used,
- why same-id different-name is a warning condition,
- which subsystems still use names for human-facing control.

## Likely Touch Points
- `src/houmao/agents/realm_controller/agent_identity.py`
- `src/houmao/agents/realm_controller/runtime.py`
- `src/houmao/agents/realm_controller/cli.py`
- `src/houmao/agents/realm_controller/manifest.py`
- `src/houmao/agents/realm_controller/registry_models.py`
- `src/houmao/agents/realm_controller/registry_storage.py`
- `src/houmao/agents/mailbox_runtime_support.py`
- mailbox registration and managed-delivery models that currently store principal- or address-based ownership only
- `src/houmao/demo/cao_interactive_demo/`
- registry, runtime, mailbox, and demo reference docs
- OpenSpec capabilities such as `agent-identity`, `brain-launch-runtime`, `agent-discovery-registry`, mailbox-related specs, and demo workflow specs

## Acceptance Criteria
1. Houmao has one shared identity model or helper layer that materializes canonical agent name plus authoritative `agent_id`.
2. When no explicit `agent_id` is supplied, the default is the full lowercase `md5(canonical_agent_name)` hex digest.
3. Runtime-owned session manifests and start-session outputs persist both canonical agent name and `agent_id`.
4. The system warns when one `agent_id` is observed with a different canonical agent name, and that warning behavior is covered by tests.
5. Shared-registry publication persists both canonical agent name and `agent_id`.
6. The shared registry provides an explicit name-to-`agent_id` resolution contract instead of assuming name-hash path derivation is still enough.
7. Mailbox registration or equivalent durable mailbox-ownership state persists enough agent-owned correlation metadata to reason about same-name versus same-agent cases.
8. Demo or tutorial persisted state records both canonical agent name and `agent_id`.
9. Reference docs explain the name-versus-`agent_id` split clearly.
10. Tests cover default derivation, explicit-id reuse warnings, registry resolution, and at least one non-registry subsystem that consumes the new identity contract.

## Non-Goals
- No requirement to replace tmux session names with `agent_id`.
- No requirement to make normal users type `agent_id` for routine runtime control.
- No requirement to replace mailbox addresses or principal ids with raw `agent_id`.
- No requirement to solve every future rename or identity-merge workflow in this single enhancement.
- No requirement to auto-migrate every existing persisted artifact in place before the first implementation lands.

## Suggested Follow-Up
- Capture this as a dedicated OpenSpec change instead of hiding it inside the narrower directory-layout change.
- Decide whether the registry should use a dedicated name index, a sidecar lookup record, or another explicit resolution surface for canonical-name lookup.
- Decide whether runtime start/build should expose explicit `--agent-id` now or keep that as an advanced/internal-only capability at first.
- Decide the minimum mailbox ownership metadata needed to prevent same-name ambiguity from leaking into mailbox lifecycle handling.
