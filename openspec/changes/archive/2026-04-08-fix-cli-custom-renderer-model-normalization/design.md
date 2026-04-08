## Context

`houmao-mgr` routes structured command output through `emit()` and the `OutputContext` print-style dispatcher. Today the generic JSON/plain/fancy fallbacks normalize Pydantic `BaseModel` payloads before rendering, but the curated plain/fancy renderer path receives the raw payload object. Managed-agent and gateway curated renderers currently expect `Mapping` input, so commands such as `agents list` and `agents gateway status` can produce correct structured data while still printing empty placeholder text in human-oriented output modes.

This is a cross-cutting output-layer issue because the contract mismatch sits in the shared dispatcher (`src/houmao/srv_ctrl/commands/output.py`) while the visible failures surface in multiple renderer modules under `src/houmao/srv_ctrl/commands/renderers/`.

## Goals / Non-Goals

**Goals:**

- Make the renderer contract consistent across `plain`, `json`, and `fancy` output paths when commands emit Pydantic models.
- Fix managed-agent inspection commands that currently drop valid data in curated human-oriented renderers.
- Preserve curated renderer formatting logic while removing the need for each renderer to handle raw `BaseModel` inputs independently.

**Non-Goals:**

- Redesign the text or rich formatting of curated renderers.
- Change managed-agent registry discovery, gateway probing, or launch behavior.
- Generalize payload normalization beyond the existing Pydantic-model contract.

## Decisions

### Normalize once in `emit()` before renderer dispatch

`OutputContext.emit()` will normalize the payload before any style-specific branching so both generic fallbacks and curated renderers receive the same renderer-safe shape.

Why this approach:

- It makes the dispatcher own one clear contract for renderer inputs.
- It prevents the same `BaseModel` bug from recurring in each curated renderer.
- It aligns the curated-renderer path with the existing JSON/plain/fancy fallback behavior already defined in the print-style spec.

Alternative considered:

- Teach each curated renderer helper to accept `BaseModel` directly.
- Rejected because it duplicates normalization logic, leaves future renderers easy to get wrong, and spreads a shared output concern across unrelated command modules.

### Keep renderer helpers working on copied mapping data

Curated renderers that mutate their local working dicts, such as launch-completion renderers that `pop("status")`, should continue to operate on copied mapping data after normalization.

Why this approach:

- It avoids side effects between normalization and rendering.
- It preserves the current renderer helper pattern where `_as_dict()` returns a detached dict.

Alternative considered:

- Let renderers mutate the normalized object directly.
- Rejected because it makes renderer behavior depend on upstream object sharing and complicates future reuse of normalized payloads.

### Add regression coverage at the output contract and command surface

Regression tests should cover both the dispatcher contract and representative commands that failed in practice.

Why this approach:

- Dispatcher-focused tests pin the actual root cause.
- Command-level tests for `agents list` and `agents gateway status` prevent silent regressions in the curated rendering path that user-controlled agents consume.

Alternative considered:

- Add renderer-only tests without exercising `emit()`.
- Rejected because the bug is specifically in dispatch-time normalization, not in the renderer formatting logic alone.

## Risks / Trade-offs

- [Risk] Some curated renderer might rely on receiving a live `BaseModel` object rather than a normalized mapping. → Mitigation: keep normalization limited to `BaseModel`, audit the curated renderers wired through `emit()`, and add regression tests for representative command paths.
- [Risk] Central normalization can mask renderer assumptions if future payload types are introduced without tests. → Mitigation: keep the renderer contract explicit in the spec and add focused unit coverage for curated renderer dispatch.
- [Trade-off] `emit()` becomes more opinionated about renderer input shape. → Accept because the shared dispatcher is the correct place to enforce a stable renderer contract.

## Migration Plan

There is no stored-data migration.

Implementation rollout:

1. Update `emit()` and/or `OutputContext.emit()` so style-specific dispatch uses normalized payloads for curated and generic renderers.
2. Keep renderer helper copy semantics intact where renderers mutate local dicts.
3. Add regression tests for managed-agent list and gateway status output in human-oriented styles.
4. Run targeted unit tests for the output engine and the affected CLI command suites.

Rollback is a code revert of the dispatcher change and its tests if an unexpected curated renderer depends on raw model objects.

## Open Questions

- No product-level open questions remain for this proposal. The only implementation-time check is whether any other curated renderer paths currently depend on raw model instances and need regression coverage in the same patch.
