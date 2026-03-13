## Context

The shared live-agent registry is now a real runtime subsystem with behavior pinned by `add-central-agent-registry`, refined by `harden-central-agent-registry`, and extended by the in-progress packaged-schema follow-up. The implementation already spans strict record models, filesystem storage helpers, runtime publication hooks, name-based fallback logic, and cleanup reporting, but the official documentation still treats the registry as a subsection of the broader realm-controller page.

That shape worked while the registry was brand new, but it is no longer enough for the current audience split:

- new users need a simple explanation of why the registry exists and when it matters,
- operators need concrete guidance on name-based lookup fallback and `cleanup-registry`,
- maintainers need exact contract and lifecycle detail without reopening change artifacts and tests.

The repository already solved a similar documentation problem for gateway, mailbox, and runtime-managed agent docs by publishing dedicated reference subtrees under `docs/reference/`. This change should follow that model so the registry gets the same durable, discoverable documentation surface.

## Goals / Non-Goals

**Goals:**
- Publish a dedicated shared-registry reference subtree under `docs/reference/registry/`.
- Split the material into focused pages for overview, contracts, operations, and internals so different questions have clear landing zones.
- Explain the shared registry as a locator layer that points to runtime-owned state rather than an authority replacement for manifests, tmux env, gateway state, or mailbox state.
- Document the implemented v1 behavior for naming, path layout, ownership, leases, malformed-record handling, cleanup behavior, and runtime publication hooks.
- Update reference navigation so readers can reach the registry docs from top-level reference pages and the broader realm-controller page.

**Non-Goals:**
- Change registry behavior, record semantics, lease duration, or runtime integration code.
- Redesign the registry around future cross-backend or cross-host behavior that the implementation does not yet provide.
- Duplicate every line of implementation detail from source files into the docs.
- Replace gateway, mailbox, or runtime-managed agent reference pages with registry-specific deep dives that belong in the new subtree.

## Decisions

### 1. Create a dedicated registry reference subtree instead of expanding `realm_controller.md`

The implementation target will be a dedicated reference directory:

- `docs/reference/registry/index.md`
- `docs/reference/registry/operations/discovery-and-cleanup.md`
- `docs/reference/registry/contracts/record-and-layout.md`
- `docs/reference/registry/contracts/resolution-and-ownership.md`
- `docs/reference/registry/internals/runtime-integration.md`

`index.md` will act as the entrypoint, define the reading path, and explain how the registry fits alongside runtime-managed agents, gateway, and mailbox docs.

Rationale:
- The registry has enough behavioral surface to justify its own navigable subtree.
- This mirrors the existing gateway and mailbox reference structure, which lowers maintenance and navigation surprise.
- It keeps `docs/reference/realm_controller.md` concise and focused on the broader runtime surface.

Alternatives considered:
- Keep one long shared-registry section in `docs/reference/realm_controller.md`.
Why not:
- It mixes overview, operations, and maintainer detail into one page and makes the registry harder to discover as its own subsystem.

### 2. Organize the docs by reader question rather than by source file

The pages will be grouped by the questions readers actually ask:

- `index.md`: what the registry is, why it exists, and where to read next,
- `operations/discovery-and-cleanup.md`: how name-based lookup fallback and cleanup behave,
- `contracts/record-and-layout.md`: what lives on disk and what the record contains,
- `contracts/resolution-and-ownership.md`: how canonical names, `agent_key`, `generation_id`, freshness, conflicts, and stale records work,
- `internals/runtime-integration.md`: where the runtime publishes, refreshes, persists, and clears registry state.

Rationale:
- New users and maintainers need different entry points.
- The code is split across models, storage, runtime, and tests, but the docs should follow conceptual seams rather than module names.
- A question-oriented structure reduces the chance that readers must reconstruct the design from multiple implementation files at once.

Alternatives considered:
- One page per implementation module such as `registry_models.py` and `registry_storage.py`.
Why not:
- That would mirror the code too closely and make the docs less useful to readers approaching the subsystem conceptually.

### 3. Make the authority boundary the central teaching device

The docs will repeatedly frame the shared registry as a secondary locator layer:

- tmux-local discovery remains the first same-host lookup path when it is present and valid,
- the shared registry is the fallback when tmux discovery is missing or stale,
- `manifest.json`, session-root artifacts, gateway artifacts, and mailbox state remain authoritative.

This framing will appear in the index, the contract pages, and the runtime-integration page.

Rationale:
- The most common misunderstanding is to treat the registry as a central state store rather than a pointer layer.
- The specs and implementation are designed around this boundary, so the docs should teach it explicitly instead of assuming readers infer it.
- This framing also helps explain why malformed or expired records resolve as stale rather than causing the system to trust central registry state over runtime-owned artifacts.

Alternatives considered:
- Lead with the filesystem layout only.
Why not:
- Readers can memorize the path layout and still miss the most important conceptual boundary.

### 4. Document the implemented v1 surface precisely and avoid implying future schema or backend behavior

The docs will describe the behavior that actually exists in the current implementation:

- tmux-backed runtime-managed sessions publish the registry,
- records are validated through strict Pydantic models,
- load-time resolution treats malformed or expired records as stale,
- `cleanup-registry` reports removed, preserved, and failed directories,
- a standalone packaged JSON Schema is planned in a separate follow-up change and should not be described as already shipped.

Rationale:
- The registry docs need to be trustworthy as an implementation reference, not a roadmap summary.
- The code and tests already pin several hardening rules that are easy to misstate if the docs are written from design memory alone.
- Being explicit about current scope avoids the same “docs read ahead of implementation” problem the gateway docs already guard against.

Alternatives considered:
- Fold in the intended future packaged-schema contract as though it were already part of the runtime boundary.
Why not:
- That would create immediate drift from the repository state and mislead maintainers inspecting installed artifacts.

### 5. Use Mermaid sequence diagrams for multi-step registry flows

Important registry procedures will be documented with embedded Mermaid `sequenceDiagram` blocks alongside prose explanation.

At minimum, diagrams should cover:

- name-based resolution with tmux-local discovery and shared-registry fallback,
- cleanup or stale-record handling where multiple actors or states interact,
- runtime publication or teardown flow where manifest persistence, gateway capability, and registry refresh sequencing matters.

Rationale:
- The registry's value is mostly in cross-artifact flow, not just static data shape.
- The repo already uses Mermaid for complex reference docs, and registry fallback logic is easier to grasp visually.
- The prose still matters, but the diagrams reduce the mental overhead of tracing the happy path and stale-path variants.

Alternatives considered:
- Prose-only procedures.
Why not:
- The fallback and publication flows are more error-prone to understand without a visual sequence.

### 6. Anchor each page to source files and behavior-defining tests

Each detailed page will identify the source files and tests that define the documented behavior, especially:

- `src/houmao/agents/realm_controller/registry_models.py`
- `src/houmao/agents/realm_controller/registry_storage.py`
- `src/houmao/agents/realm_controller/runtime.py`
- `tests/unit/agents/realm_controller/test_registry_storage.py`
- `tests/unit/agents/realm_controller/test_runtime_agent_identity.py`
- `tests/unit/agents/realm_controller/test_runtime_registry.py`
- `tests/integration/agents/realm_controller/test_registry_runtime_contract.py`

Rationale:
- The registry contract is split between implementation and tests, and maintainers need a durable trace from docs to source.
- This also makes the docs easier to keep in sync when registry behavior changes later.

Alternatives considered:
- Mention only source modules and omit tests.
Why not:
- Several important semantics, especially failure isolation and stale handling, are clearest in the tests that pin them.

## Risks / Trade-offs

- [Risk] The registry subtree may overlap with the existing runtime-managed agent docs and create duplicate explanations. -> Mitigation: keep the broader agent docs high-level and let the registry subtree own registry-specific deep detail.
- [Risk] The docs could drift from the hardening semantics or the schema follow-up state. -> Mitigation: anchor each page to current source files and tests, and explicitly scope the docs to implemented v1 behavior.
- [Risk] A question-oriented split could feel fragmented if the landing page is weak. -> Mitigation: make `index.md` a strong reading guide with reader-oriented descriptions and related-reference links.
- [Risk] Mermaid diagrams can become noisy if they try to cover too many branches at once. -> Mitigation: keep one primary diagram per important flow and let prose explain edge cases separately.

## Migration Plan

1. Create the `docs/reference/registry/` subtree with the planned page layout.
2. Write the pages from the current registry specs, implementation, and tests while normalizing terminology and scope to implemented behavior.
3. Update `docs/reference/index.md` and `docs/reference/realm_controller.md` so the new subtree is discoverable and the old embedded registry section becomes a concise summary.
4. Re-read the final docs against the registry code paths and tests to confirm that contracts, fallback behavior, and failure boundaries are described consistently.

Rollback strategy:
- Because this is documentation-only, rollback is a content and navigation revert. No runtime migration or state transition is required.

## Open Questions

- None at proposal time. The remaining work is primarily editorial execution rather than product or architecture uncertainty.
