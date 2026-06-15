## Context

The completed but unarchived `split-ag-ui-graphing-system-skill` change added `houmao-utils-graphing` as a graphing authoring skill and placed it in `core` so `houmao-interop-ag-ui` could delegate chart authoring to it. The new requirement changes that model: graphing should be an extension, installed by default but not treated as a dependency of non-extension skills.

The current system-skill catalog already resolves arbitrary named sets from `catalog.toml`, and the schema accepts kebab-case set names. The change can therefore introduce an `extensions` named set without adding a new catalog field or visible family directory.

```text
Before
core/all
  -> houmao-interop-ag-ui
       -> routes to houmao-utils-graphing

After
core
  -> houmao-interop-ag-ui

extensions
  -> houmao-ext-graphing

default install
  -> core + extensions

routing boundary
  -> non-extension skills do not depend on extension skills
```

## Goals / Non-Goals

**Goals:**

- Rename `houmao-utils-graphing` to `houmao-ext-graphing` everywhere it is packaged, installed, listed, tested, and documented.
- Introduce `extensions` as the installable category for default-installed but optional extension skills.
- Remove `houmao-ext-graphing` from `core` while keeping it installed by managed launch, managed join, and CLI-default flows through default set selection.
- Remove non-extension-to-extension skill routing, starting with `houmao-interop-ag-ui`.
- Retire `houmao-utils-graphing` so reinstall and uninstall operations clean up stale old-name projections.

**Non-Goals:**

- Do not change AG-UI protocol, implementation schema, Plotly.js, or Vega-Lite behavior.
- Do not add a new graphing backend or frontend component contract.
- Do not introduce visible `extensions/` family directories in installed skill homes.
- Do not require agents to use the graphing extension when they are only doing AG-UI protocol or gateway delivery work.

## Decisions

### Use `extensions` as a named set and logical category

The packaged catalog should add `[sets.extensions]` with `houmao-ext-graphing` as its initial member. The existing flat projection model stays unchanged, so Codex and Claude still install to `skills/houmao-ext-graphing/`, and Gemini still installs to `.gemini/skills/houmao-ext-graphing/`.

Alternative considered: add a `category = "extensions"` field to each skill record. That would make category metadata explicit, but the current runtime selection mechanism is already set-based. A new field would need schema, parser, CLI, and docs changes without improving install behavior for this change.

### Keep extension skills default-installed without making them core

The catalog should select both `core` and `extensions` for managed launch and managed join:

```toml
managed_launch_sets = ["core", "extensions"]
managed_join_sets = ["core", "extensions"]
cli_default_sets = ["all"]
```

The `all` set should include all current packaged skills, including `extensions`. An explicit `--skill-set core` install should exclude `houmao-ext-graphing`; default install paths should include it.

Alternative considered: keep graphing in `core` because it is installed by default. That keeps resolved lists shorter, but it makes the extension impossible to ignore as a category and preserves the unwanted dependency edge from non-extension skills.

### Treat extension activation as user-intent-driven

Non-extension skills should not tell agents to invoke `houmao-ext-graphing`, list it as a required related skill, or present it as a delegated workflow. `houmao-interop-ag-ui` should describe protocol validation, implementation rendering for already-chosen payloads, gateway publishing, endpoint selection, and delivery result interpretation. It should not route chart-authoring requests to the graphing extension.

The graphing extension may still refer to `houmao-interop-ag-ui` for AG-UI event delivery because extension-to-core references do not make core behavior depend on the extension.

Alternative considered: keep a short graphing handoff in `houmao-interop-ag-ui` while marking it optional. That still creates a non-extension-to-extension routing edge and conflicts with the user's ability to ignore extension guidance.

### Retire the old utility name

`houmao-utils-graphing` should move to `retired_skill_names`. Install and uninstall operations already remove retired Houmao-owned projections, so the rename can clean stale copied or symlinked assets without a compatibility shim.

Alternative considered: keep an alias or duplicate skill under the old name. This would reduce short-term friction for users who already learned the old name, but the repository is still unstable and the duplicate would keep the wrong category visible.

## Risks / Trade-offs

- Existing tests and docs may still assume only `core` and `all` named sets -> Update catalog, CLI, and docs tests to include `extensions`.
- Users may expect default-installed skills to be in `core` -> Document that default install uses multiple sets and that `core` is the non-extension baseline.
- Prompt text can accidentally recreate the old routing edge -> Add tests or grep-backed assertions that non-extension assets do not mention `houmao-ext-graphing` as a route target.
- Stale homes may contain `houmao-utils-graphing` -> Add the old name to retired-skill cleanup and cover install/uninstall behavior.

## Migration Plan

1. Rename the asset directory and internal metadata from `houmao-utils-graphing` to `houmao-ext-graphing`.
2. Register `houmao-ext-graphing` in the packaged catalog, add `extensions`, remove graphing from `core`, and keep it in `all`.
3. Update auto-install set lists so managed launch and join resolve `core` plus `extensions`.
4. Add `houmao-utils-graphing` to retired names.
5. Remove graphing-extension routing from `houmao-interop-ag-ui`.
6. Update docs and tests for the new name, set membership, default install behavior, and routing boundary.

Rollback before archive can restore the previous asset name, remove the `extensions` set, and return default install lists to their previous values. After archive, rollback should be a new change because the installed skill inventory and retired-name cleanup contract will have changed.

## Open Questions

- Should future extension skills all be default-installed, or should `extensions` later split into default and optional extension sets? This change treats the initial extension as default-installed because the user requested that behavior.
