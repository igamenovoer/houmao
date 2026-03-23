# Feature Request: Move CAO-Compatible HTTP Surface Behind an Explicit `houmao-server` Compatibility Namespace

## Status
Proposed

## Summary
Reshape `houmao-server` so CAO-compatible HTTP behavior lives behind an explicit compatibility boundary instead of defining the outer shape of the server forever.

The current server still exposes CAO-shaped root routes such as:

- `/sessions`
- `/sessions/{session_name}`
- `/terminals/{terminal_id}`
- `/terminals/{terminal_id}/input`

That is useful for migration, but it makes the top-level server API look like a CAO replacement rather than a Houmao-native control plane.

The requested direction is:

- treat CAO-compatible routes as a compatibility namespace or compatibility mode
- treat Houmao-native routes as the canonical long-term server surface

## Why
The project direction is to grow into a Houmao-native framework, not to remain permanently constrained by CAO’s route model.

Today the CAO-shaped root routes create several problems:

- they imply that CAO compatibility is the primary public identity of `houmao-server`
- they pressure new native features to fit around CAO route assumptions
- they blur the boundary between migration support and long-term API design
- they make the Houmao-native routes look additive or secondary even when they are the more strategic surface

Recent headless work makes this mismatch obvious:

- native headless lifecycle already uses Houmao-owned routes under `/houmao/agents/*`
- native managed-agent identity no longer depends on CAO `terminal_id`
- server-owned authority now lives under `state/managed_agents/<tracked_agent_id>/`

But despite that, the server still presents CAO-compatible root routes as the outer public shape.

## Desired API Boundary
The canonical separation should be:

- explicit CAO compatibility surface:
  - for example `/cao/...`, `/compat/cao/...`, or an equivalent versioned compatibility namespace
- Houmao-native surface:
  - top-level or primary Houmao-owned routes whose semantics are defined by Houmao

The exact final URL shape should be decided in design work, but the important boundary is conceptual:

- CAO compatibility should be visibly compatibility-scoped
- Houmao-native APIs should not need to live permanently under a secondary `/houmao/...` subtree just because CAO currently owns the root

## Requested Scope
1. Introduce an explicit server-side CAO compatibility boundary for the migrated CAO route family.
2. Define the Houmao-native API surface as the preferred canonical interface for new capabilities.
3. Stop treating CAO route shape as the long-term constraint on top-level HTTP resource design.
4. Provide a staged migration path for existing callers that depend on CAO-compatible routes.
5. Document clearly which parts of the server API are:
   - CAO compatibility
   - Houmao-native
   - temporary compatibility shims
6. Ensure future native features can land on Houmao-designed resources without needing to preserve CAO naming or route conventions.

## Acceptance Criteria
1. The CAO-compatible route family is available through an explicit compatibility-scoped boundary.
2. Houmao-native APIs are documented as the preferred long-term interface.
3. New native server features no longer need to treat the CAO root route family as the canonical outer API shape.
4. Existing CAO-oriented clients have a documented compatibility path or migration plan.
5. Docs clearly explain that CAO compatibility is transitional and does not define the long-term `houmao-server` information architecture.
6. Tests cover at least:
   - one CAO-compatible route through the compatibility boundary
   - one Houmao-native route that remains outside the CAO compatibility contract

## Non-Goals
- No requirement to remove CAO-compatible routes immediately.
- No requirement to break existing migration clients in one step.
- No requirement to finalize the entire long-term Houmao HTTP API architecture in the same change.
- No requirement to remove child-CAO support immediately while terminal-backed compatibility still depends on it.

## Suggested Migration Shape
One reasonable staged path is:

1. Add an explicit CAO compatibility namespace or equivalent server boundary.
2. Keep current root-level CAO routes temporarily as compatibility aliases or shims.
3. Expand Houmao-native APIs as the preferred documented interface.
4. Route new native capabilities only through Houmao-owned resources.
5. Deprecate or narrow old root-level CAO-shaped aliases once clients have a supported migration path.

## Strategic Outcome
This change would make the server boundary honest:

- CAO compatibility remains available where it helps short-term migration
- but it stops defining the long-term public identity of `houmao-server`
- which lets Houmao evolve its HTTP model around managed agents, native lifecycle control, and Houmao-owned resource design instead of inheriting CAO’s route tree indefinitely

## Suggested Follow-Up
- Create an OpenSpec change for `houmao-server` API boundary redesign.
- Audit current server routes and classify each one as:
  - CAO compatibility
  - Houmao-native
  - temporary shim
- Decide whether the long-term preferred shape is:
  - a namespaced compatibility tree such as `/cao/...`
  - a dedicated compatibility mode/listener
  - or another explicit boundary with equivalent clarity
- Update migration and reference docs so users understand that CAO compatibility is a migration aid, not the final public server architecture.
