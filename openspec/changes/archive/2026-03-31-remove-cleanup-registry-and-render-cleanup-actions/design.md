## Context

`houmao-mgr` cleanup behavior is currently split between two concerns that were implemented independently:

- command routing still exposes both `admin cleanup registry` and the older `admin cleanup-registry` alias,
- cleanup commands already produce detailed structured action lists, but their default human-oriented rendering falls back to the generic nested-dict renderer.

That fallback is the practical usability problem. Cleanup payloads already carry `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions`, each with artifact kind, path, reason, and optional details. In plain mode, those nested lists are rendered as `[n items]` and `{...}`, so operators do not actually see what was or would be cleaned unless they switch to JSON.

This change is cross-cutting because the same cleanup payload shape is emitted by:

- `houmao-mgr admin cleanup ...`,
- `houmao-mgr agents cleanup ...`,
- `houmao-mgr mailbox cleanup`,
- `houmao-mgr project mailbox cleanup`.

The repository is also in an unstable phase and explicitly permits breaking cleanup-path changes when the grouped command tree is clearer than preserving legacy aliases.

## Goals / Non-Goals

**Goals:**

- Make `houmao-mgr admin cleanup registry` the only supported native cleanup path for shared-registry cleanup.
- Keep cleanup JSON payloads stable for tests, automation, and machine consumers.
- Make human-oriented cleanup output show each actionable artifact line by line instead of only top-level counts.
- Reuse one cleanup rendering strategy across all commands that emit the normalized cleanup payload shape.
- Update docs and tests so the supported cleanup path and operator-visible output match the implementation.

**Non-Goals:**

- Change cleanup classification logic, safety rules, or dry-run semantics.
- Redesign the generic output fallback for every nested payload in `houmao-mgr`.
- Remove the separate deprecated realm-controller compatibility CLI `cleanup-registry` entrypoint.
- Introduce a new cleanup payload schema or rename existing JSON fields.

## Decisions

### Decision 1: Remove the native `houmao-mgr admin cleanup-registry` alias entirely

The native `houmao-mgr` admin tree will stop registering `cleanup-registry` and will only support `admin cleanup registry`.

Rationale:

- The grouped cleanup tree is already the documented primary surface.
- The alias adds help noise and keeps tests and docs split across two paths.
- This repository explicitly allows breaking CLI cleanup changes when they simplify the supported surface.

Alternatives considered:

- Keep the alias indefinitely: rejected because it preserves duplicate surface area for little value.
- Keep the alias but hide it from docs: rejected because the command would still be discoverable in help and tests, so the contract would remain ambiguous.

### Decision 2: Add a shared cleanup-specific renderer instead of changing the generic fallback

Cleanup commands will use a dedicated renderer for plain and fancy output. The renderer will consume the existing normalized cleanup payload shape and print outcome buckets with one line per action.

The generic `emit()` fallback remains unchanged for non-cleanup payloads.

Rationale:

- The problem is specific to cleanup payloads, not to every nested dict in the CLI.
- A dedicated renderer avoids accidental formatting regressions in unrelated command families.
- The normalized cleanup payload already gives us one stable contract to render from.

Alternatives considered:

- Teach the generic plain renderer to expand all nested dict/list structures recursively: rejected because it would affect many unrelated commands and would be hard to keep readable.
- Add per-command renderers for admin, agents, mailbox, and project cleanup separately: rejected because the payload shape is intentionally shared and should render consistently everywhere.

### Decision 3: Keep JSON output unchanged and treat rendering as a view concern

The structured cleanup payload contract remains the source of truth. Human-oriented rendering will be layered on top of the existing payload fields rather than introducing parallel human-only result objects.

That means:

- `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions` remain unchanged,
- summary counts remain available as supporting information,
- JSON output continues to expose the same machine-readable structure.

Rationale:

- Existing tests and automation already consume the JSON shape.
- The current issue is missing human visibility, not missing structured data.
- Keeping one payload contract lowers implementation and migration risk.

Alternatives considered:

- Create a second cleanup-specific payload optimized for plain text: rejected because it duplicates semantics already present in the shared cleanup payload.
- Remove summary counts once line-by-line rendering exists: rejected because summary counts are still useful as footer-level aggregation and for JSON consumers.

### Decision 4: Human-oriented cleanup output should be grouped by outcome, not only by command scope

The cleanup renderer will organize output around the action buckets that operators actually need to evaluate:

- planned,
- applied,
- blocked,
- preserved.

Each non-empty bucket will list one artifact per line with enough context to understand what happened or would happen, including path, artifact kind, reason, and compact details when present.

Rationale:

- Cleanup review is primarily about what was removed, what would be removed, and what was intentionally preserved or blocked.
- Grouping by outcome preserves the semantics already encoded in the payload.
- This works consistently across registry, runtime, mailbox, and session-scoped cleanup commands.

Alternatives considered:

- Print only removed/planned lines and hide preserved lines: rejected because cleanup safety often depends on understanding why artifacts were preserved.
- Print only a table with no bucket grouping: rejected because dry-run and execute semantics become harder to scan when outcome classes are mixed together.

### Decision 5: Scope the contract and docs changes to `houmao-mgr` and registry cleanup guidance

The spec and docs updates will cover:

- removal of the native `houmao-mgr admin cleanup-registry` requirement,
- updated `houmao-mgr` cleanup behavior and help expectations,
- registry operations docs that currently still describe the legacy alias and bucket-only cleanup interpretation.

The deprecated realm-controller compatibility CLI remains out of scope for this change.

Rationale:

- The user request is about `houmao-mgr admin cleanup`.
- The realm-controller CLI is already explicitly deprecated and should be handled by a separate retirement change if needed.

Alternatives considered:

- Remove every `cleanup-registry` command in the repo in one change: rejected because it mixes supported-surface cleanup with legacy-entrypoint retirement.

## Risks / Trade-offs

- [Risk] Removing the alias breaks local scripts or habits that still call `houmao-mgr admin cleanup-registry`. → Mitigation: document the migration directly and keep the replacement path trivial: `houmao-mgr admin cleanup registry`.
- [Risk] Cleanup renderer formatting could drift across command families if some call sites keep using generic `emit()`. → Mitigation: route every normalized cleanup emitter through one shared cleanup renderer helper.
- [Risk] Printing preserved actions line by line may produce verbose output on large cleanup runs. → Mitigation: keep the renderer bucketed and compact, with summary counts retained as a footer.

## Migration Plan

1. Remove the native `houmao-mgr admin cleanup-registry` command registration and its help/tests/docs references.
2. Introduce shared cleanup plain/fancy renderers and use them at all cleanup emit sites that already return the normalized cleanup payload.
3. Update cleanup tests to assert the new supported command path and the presence of per-action human output.
4. Update CLI and registry reference docs to use `houmao-mgr admin cleanup registry` and to explain the new action-by-action cleanup output.

## Open Questions

No open questions remain for this proposal.
