## Context

The `houmao-mgr internals graph` command group was added (ec4e25ab) but skipped the docs site. The CLI has two nested groups — `graph high` (Houmao-aware loop helpers) and `graph low` (generic NetworkX primitives plus `alg` subgroup) — implemented in `src/houmao/srv_ctrl/commands/internals.py`. The existing `docs-cli-reference` spec's list of required command groups predates `internals` and must be extended. No new code is written; all changes are documentation and spec files.

## Goals / Non-Goals

**Goals:**
- Add `docs/reference/cli/internals.md` with a full subcommand reference for `graph high` and `graph low`.
- Add an `### internals` section to `docs/reference/cli/houmao-mgr.md` that links to the new page.
- Add an `internals` entry to the CLI surfaces section of `docs/index.md`.
- Add a brief note to `docs/getting-started/system-skills-overview.md` pointing loop-skill users to `graph high` tooling.
- Extend the `docs-cli-reference` spec to require `internals` in the documented command group list.
- Create a new `docs-internals-graph-cli-reference` spec.

**Non-Goals:**
- Changes to runtime code, CLI behavior, or skill assets.
- Full audit of all docs against the codebase — this change targets the specific internals gap.
- Coverage of `houmao-mgr internals` beyond the current `graph` subgroup.

## Decisions

### New page structure for `internals.md`

The `graph high` and `graph low` surfaces are substantial (5 high commands, 7 low commands, 13 alg commands). A dedicated page mirrors how `agents-gateway.md` and `agents-turn.md` are handled — the main `houmao-mgr.md` gets a pointer section, and the dedicated page holds the full option tables.

`graph low alg` commands share a single option schema (`--input`, `--node`, `--source`, `--target`, `--distance`, `--cutoff`, `--length-bound`, `--limit`), so a shared options table plus a subcommand summary table is more readable than repeating options per-command.

### Delta spec for `docs-cli-reference`

The existing `docs-cli-reference/spec.md` has a single requirement that lists the command groups. Rather than rewriting the entire requirement, a MODIFIED block with the updated list (adding `internals`) plus a new scenario for `internals` discoverability is sufficient.

### Placement of the system-skills-overview note

The note about graph tooling belongs in the `houmao-agent-loop-pairwise-v2` and `houmao-agent-loop-generic` skill rows (or just after the loop-skills table) rather than in a separate section — it's a brief "see also" pointer, not a full tutorial.

## Risks / Trade-offs

- **Risk**: `graph low alg` has 13 commands; full per-command tables would bloat the page.
  → **Mitigation**: Group them in a summary table, with the shared option schema described once above the table.

- **Risk**: `docs-cli-reference` spec currently lists 7 command groups; if future groups are added without updating the spec, the spec becomes stale again.
  → **Mitigation**: The new spec requirement is written as "at minimum, SHALL include … `internals`" rather than an exhaustive closed list.

## Migration Plan

No migration needed — purely additive documentation. Existing docs are not removed or restructured.

1. Write `docs/reference/cli/internals.md` (new file).
2. Add `### internals` section to `docs/reference/cli/houmao-mgr.md`.
3. Add `internals` link to `docs/index.md`.
4. Add graph-tooling note to `docs/getting-started/system-skills-overview.md`.
5. Write delta spec `openspec/specs/docs-cli-reference/spec.md`.
6. Write new spec `openspec/specs/docs-internals-graph-cli-reference/spec.md`.

## Open Questions

None — the implementation scope is clear from the existing source and the `houmao-mgr-internals-graph-cli` spec that already specifies the CLI behavior.
