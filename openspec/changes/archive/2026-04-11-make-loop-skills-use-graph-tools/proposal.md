## Why

The internal `houmao-mgr internals graph high` tools now provide deterministic topology analysis, slicing, packet expectations, packet validation, and Mermaid scaffolding. The loop skills should use that supported manager surface as their first-class structural preflight instead of leaving agents to re-derive graph facts from prose whenever node-link graph and packet artifacts exist.

## What Changes

- Tighten `houmao-agent-loop-pairwise-v2` guidance so the default `precomputed_routing_packets` path treats graph-tool analysis, packet expectation derivation, and packet validation as the preferred authoring and initialization path when the plan has machine-readable topology and packet artifacts.
- Require pairwise-v2 guidance to keep runtime intermediate agents out of graph reasoning: they use dispatch tables and exact precomputed child packets, while graph analysis happens before `ready`.
- Tighten `houmao-agent-loop-generic` guidance so authored generic loop plans use `graph high analyze`, `slice`, and `render-mermaid` as deterministic structural helpers when a node-link graph is available.
- Preserve the semantic boundary: loop skills remain responsible for delegation policy, result routing, forbidden actions, lifecycle vocabulary, and final graph review; graph tools only provide structural evidence.
- Keep `houmao-mgr internals graph high` itself unchanged; this change is about making loop-skill usage of the existing manager internals explicit and operationally consistent.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v2-skill`: strengthen graph-tool usage for default routing-packet authoring and initialization.
- `houmao-agent-loop-generic-skill`: strengthen graph-tool usage for generic loop structural analysis, slicing, and Mermaid scaffolding.

## Impact

- Affected assets:
  - `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/`
  - `src/houmao/agents/assets/system_skills/houmao-agent-loop-generic/`
- Affected specs:
  - `openspec/specs/houmao-agent-loop-pairwise-v2-skill/spec.md`
  - `houmao-agent-loop-generic-skill` delta coverage carried by this change
- Affected tests:
  - targeted system-skill content checks for the loop-skill graph-tool guidance
- No new runtime loop engine, graph CLI command, mailbox transport, gateway API, or dependency is introduced.
