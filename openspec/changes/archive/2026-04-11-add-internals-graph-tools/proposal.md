## Why

The generic and pairwise loop skills now require agents to reason about directed communication graphs, descendant relationships, component dependencies, and pairwise-v2 routing-packet coverage. That reasoning is easy to get subtly wrong in prose, so Houmao should provide a NetworkX-backed internal graph-analysis CLI that agents can use as a deterministic calculator during authoring and validation.

## What Changes

- Add a top-level `houmao-mgr internals` command family with `graph high ...` and `graph low ...` subtrees.
- Standardize graph interchange for the new graph tooling on NetworkX node-link JSON only, using directed multigraph semantics by default.
- Add `graph high` commands for Houmao-aware loop-graph analysis, pairwise-v2 routing-packet expectations, packet validation, authoring-time subtree slicing, and deterministic Mermaid rendering support.
- Add `graph low` commands that expose constrained NetworkX-style graph construction, mutation, transformation, and algorithm wrappers for agents that need direct graph primitives.
- Keep high-level commands structural and fail-closed: they SHALL NOT infer free delegation, repair stale packets, or replace the loop skills' planning responsibilities.
- Update loop-skill authoring guidance to prefer `graph high` for routing-packet validation, descendant checks, and graph rendering support while preserving skill-owned semantic review.

## Capabilities

### New Capabilities

- `houmao-mgr-internals-graph-cli`: Defines the `houmao-mgr internals graph` command family, node-link JSON graph contract, high-level Houmao loop graph tools, and low-level NetworkX-backed graph primitives.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: Add `internals` as a supported top-level native command family and document it as a Houmao-owned internal utility surface.
- `houmao-agent-loop-pairwise-v2-skill`: Update pairwise-v2 authoring and initialization guidance so default precomputed routing-packet preparation can use `houmao-mgr internals graph high` for topology analysis, packet expectations, and packet validation.

## Impact

- Affected runtime code:
  - `src/houmao/srv_ctrl/commands/main.py`
  - new `src/houmao/srv_ctrl/commands/internals.py`
  - new graph helper modules under `src/houmao/agents/`
- Affected skill assets:
  - `src/houmao/agents/assets/system_skills/houmao-agent-loop-generic/`
  - `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/`
- Affected tests:
  - CLI command inventory/help tests
  - graph helper unit tests
  - targeted system-skill content checks
- Dependencies:
  - Uses existing `networkx` project dependency.
  - No new external package is required.
