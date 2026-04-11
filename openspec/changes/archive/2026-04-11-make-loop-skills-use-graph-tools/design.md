## Context

`houmao-mgr internals graph high` now exposes Houmao-aware structural graph helpers over NetworkX node-link JSON. The pairwise-v2 skill already has a default `precomputed_routing_packets` strategy, and the generic loop skill already decomposes plans into typed pairwise and relay components. Both skills mention the graph helpers, but their current guidance still leaves too much of the structural preflight as optional prose reasoning.

The design intent is to move graph-derived facts out of agent memory and into deterministic manager calls whenever the plan has machine-readable artifacts. The loop skills still own plan semantics; the graph tools own structural facts such as reachability, leaves, non-leaf participants, child relationships, descendant slices, packet expectations, packet validation, and Mermaid scaffolding.

## Goals / Non-Goals

**Goals:**

- Make `houmao-mgr internals graph high` the first-class structural helper for loop-skill authoring and initialization when NetworkX node-link graph artifacts are available.
- Make pairwise-v2 use `analyze`, `slice`, `packet-expectations`, and `validate-packets` as the expected plan-time and prestart sequence for default `precomputed_routing_packets` runs that have graph and packet JSON artifacts.
- Make generic loop planning use `analyze`, `slice`, and `render-mermaid` as deterministic structural support while keeping final semantic review in the generic skill.
- Keep runtime intermediate agents simple: they follow dispatch tables and append exact child packets rather than recomputing graph topology or descendant slices.
- Preserve the fail-closed packet behavior from the existing graph-tool contract.

**Non-Goals:**

- Do not add new graph CLI commands, new graph formats, or a new runtime loop engine.
- Do not require ordinary users to author raw NetworkX JSON by hand for every small plan.
- Do not make `graph low` part of routine loop-skill guidance.
- Do not let graph tooling infer delegation authority, result-routing authority, forbidden-action policy, or final lifecycle state.
- Do not auto-repair missing, mismatched, or stale routing packets from graph topology.

## Decisions

### 1. Treat graph artifacts as the deterministic preflight source when present

Pairwise-v2 and generic guidance should say that, when a NetworkX node-link graph exists, agents use `graph high` rather than re-deriving root reachability, leaf/non-leaf posture, child relationships, component dependency posture, or descendant slices from prose.

Rationale: this directly uses the new manager-owned graph analysis surface and reduces repeated graph reasoning at intermediate nodes.

Alternative considered: keep the current wording as a conditional hint. That preserves flexibility, but it makes graph-tool usage easy to skip even for complex plans where structural mistakes are expensive.

### 2. Keep graph-tool use in authoring and initialization, not runtime handoff

For pairwise-v2, graph-tool usage belongs before `ready`: `analyze` and optional `slice` during packet authoring, `packet-expectations` to derive required routing artifacts, and `validate-packets` before default initialization completes. Once the run starts, intermediate agents only read their packet dispatch tables and append exact child packet text or exact packet references.

Rationale: this matches the routing-packet cascade design and prevents long-running tasks from drifting into ad hoc runtime graph reconstruction.

Alternative considered: allow intermediate agents to call `graph high slice` if confused. That would create a repair path from stale or partial memory, undermining fail-closed packet behavior.

### 3. Keep generic loop usage to high-level structural helpers

Generic loop guidance should reference `graph high analyze`, `slice`, and `render-mermaid`. It should not teach routine authors to use `graph low` algorithms or transforms.

Rationale: the generic loop skill is a semantic planner for typed components, policies, and result routing. Low-level graph primitives are useful for maintainers and future tooling, but routine skill guidance should stay on the Houmao-aware high-level surface.

Alternative considered: document `graph low` as a fallback for generic loop graph reasoning. That gives more tools to advanced agents, but it encourages raw graph manipulation where the skill should preserve typed component semantics.

### 4. Keep semantic authority in the loop skills

Graph-tool output should be described as structural evidence. The skill guidance still validates delegation policy, result-routing contracts, forbidden actions, lifecycle vocabulary, stop/completion posture, and final graph semantics.

Rationale: `graph high` intentionally does not infer free delegation, hidden dependencies, final loop policy, or semantic correctness of packet prose.

Alternative considered: treat successful graph validation as full plan readiness. That would over-trust structural checks and could miss policy or lifecycle mistakes.

## Risks / Trade-offs

- Agents may over-treat `validate-packets` success as complete plan validation. Mitigation: require loop-skill wording and tests to preserve the structural-only boundary.
- Machine-readable graph artifacts may be unavailable for small or legacy plans. Mitigation: make graph-tool usage required when the artifacts are available, while still requiring explicit visible topology and packet coverage when they are not.
- Generic-loop changes could conflict with the still-open completed generic-loop proposal. Mitigation: keep this change focused on graph-tool preflight wording and avoid reworking the generic skill capability itself.
- More command references in skill docs may make guidance noisier. Mitigation: keep the routine flow to `graph high` only and avoid documenting `graph low` in loop-skill pages.

## Migration Plan

Update the pairwise-v2 and generic loop skill assets in place. Add targeted system-skill content checks to assert that the graph-tool-first preflight language and semantic boundaries are present. No runtime migration is required because the graph CLI already exists and the change only revises packaged skill guidance.

Rollback is limited to reverting the skill guidance and content checks; no stored data or runtime API changes are involved.

## Open Questions

None.
