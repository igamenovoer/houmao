## Context

Houmao ships three loop skills that differ in lifecycle vocabulary, prestart model, and graph topology support. A reader following the README sees only `houmao-agent-loop-pairwise` in detail (§4). The `pairwise-v2` skill changed its default prestart strategy from operator mail wave to plan-time routing packets — a behavioral change with no conceptual page explaining what routing packets are or how to author them. The `houmao-agent-loop-generic` skill is new and only visible in the skill catalog table. The `internals graph` commands that support loop authoring also have no README entry point.

All content targets the existing docs site structure and README format — no new subsystems, dependencies, or infrastructure.

## Goals / Non-Goals

**Goals:**
- New page `docs/getting-started/loop-authoring.md` that gives readers:
  - A skill-selection reference table (pairwise / pairwise-v2 / generic — when to use which)
  - A concise explanation of the pairwise-v2 routing-packet prestart model
  - An introduction to generic loop graph decomposition (pairwise + relay components)
  - Pointers to `houmao-mgr internals graph high` as the authoring-time validation toolchain
  - Links to each skill's SKILL.md for the full lifecycle vocabulary
- `docs/index.md`: link to the new page from Getting Started
- `README.md §4`: note all three loop options and link to the guide; current pairwise example stays as the worked example
- `README.md CLI Entry Points`: add an `internals graph` note/entry

**Non-Goals:**
- Full pairwise-v2 lifecycle reference (that lives in the skill's SKILL.md and operating pages)
- Tutorial content for generic loop graph authoring beyond an orientation paragraph
- Changes to the three loop skill assets or any runtime code

## Decisions

### Page placement: getting-started, not reference

The loop authoring guide is conceptual orientation — "which skill, and how does the model work" — not a command reference. Getting-started is the right home. The reference for each skill lives in SKILL.md and the CLI surfaces.

### README §4: extend, don't replace

The worked pairwise example in §4 is the most concrete illustration of the agent-loop model. Replacing it loses the value of a concrete story-writing walkthrough. Instead, add a brief "Three loop options" block before the pairwise example that names all three skills with one-line descriptions, then let the existing pairwise detail remain as the canonical entry-level example.

### README internals entry: note under houmao-mgr, not a new row

`internals graph` is a subcommand group of `houmao-mgr`, not a standalone entrypoint. A parenthetical note under the `houmao-mgr` row (e.g., "includes `internals graph` for loop-plan graph analysis and packet validation") is more accurate than a separate row. Alternatively, a dedicated "Internal tooling" row is also defensible — the choice should not duplicate the CLI entry points table.

### Routing-packet explanation depth

The guide explains the concept in 3-4 sentences: what a routing packet is (a precomputed instruction block the master puts in the plan), what `initialize` does with it (validates packet coverage before start), and how `graph high packet-expectations` and `validate-packets` help. It does not reproduce the full packet JSON schema — that lives in the skill's prestart page.

## Risks / Trade-offs

- **Risk**: Page goes stale if pairwise-v2 routing-packet semantics change again.
  → **Mitigation**: Keep the conceptual explanation at a high level; point to SKILL.md for specifics.

- **Risk**: "Three loop options" in README §4 bloats the quick-start.
  → **Mitigation**: Three one-line entries in a small table, then the existing pairwise walkthrough.

## Migration Plan

No migration. Purely additive docs changes. Existing skill SKILL.md files and operating pages are unchanged.

1. Write `docs/getting-started/loop-authoring.md`
2. Update `docs/index.md`
3. Update `README.md §4` and CLI Entry Points
4. Write delta specs and new spec

## Open Questions

None. Scope is clear from the explored codebase.
