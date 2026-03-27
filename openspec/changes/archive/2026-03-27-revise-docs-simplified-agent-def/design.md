## Context

The `simplify-agent-definition-model` change (completed, all 12 tasks done) restructured the agent definition directory from a "brains-first" layout to a "role/tool-first" layout. The getting-started docs (`agent-definitions.md`, `quickstart.md`, `overview.md`) and CLI reference docs (`cli.md`, `cli/houmao-mgr.md`) were updated as part of that change. However, the project README, three build-phase reference docs, and all four LLM context files still describe the old model.

Current terminology mapping (old → new):
- `brains/tool-adapters/<tool>.yaml` → `tools/<tool>/adapter.yaml`
- `brains/cli-configs/<tool>/<profile>/` → `tools/<tool>/setups/<setup>/`
- `brains/api-creds/<tool>/<profile>/` → `tools/<tool>/auth/<auth>/`
- `brains/brain-recipes/<tool>/*.yaml` → `roles/<role>/presets/<tool>/<setup>.yaml`
- `brains/skills/<skill>/` → `skills/<skill>/`
- `blueprints/*.yaml` → removed (preset path derivation replaces recipe+blueprint layering)
- `config_profile` → `setup`
- `credential_profile` → `auth`
- `BrainRecipe` → `AgentPreset` (path-derived from preset YAML)

The getting-started docs are the canonical reference for the new layout. The deleted build-phase reference docs overlap with them and describe exclusively the old model.

## Goals / Non-Goals

**Goals:**

- Eliminate all references to the old `brains/`-first directory layout, recipe/blueprint terminology, and old CLI flag names (`--recipe`, `--config-profile`, `--cred-profile`) from documentation and LLM context files.
- Delete three obsolete reference docs whose content is now covered by the getting-started section.
- Rewrite the README's agent-definition walkthrough section to be self-contained with the new layout, including inline examples derived from `tests/fixtures/agents/`.
- Update all four LLM context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) so AI agents working in this repo generate code against the new model.
- Keep `mkdocs.yml` navigation consistent after deletions.
- Fix old-path references in surviving reference docs.

**Non-Goals:**

- Migrating fixture directory trees (`tests/fixtures/agents/brains/` etc.) — the old directories still exist as compatibility stubs and are not documentation's concern.
- Rewriting any docs that are already current (getting-started, CLI reference, gateway, mailbox, registry, etc.).
- Adding new documentation pages.
- Changing runtime code.

## Decisions

### Delete rather than rewrite obsolete build-phase reference docs

Delete `docs/reference/agents_brains.md`, `docs/reference/build-phase/brain-builder.md`, and `docs/reference/build-phase/recipes-and-adapters.md` rather than rewriting them.

Why this over rewriting: the getting-started docs (`overview.md` for the two-phase lifecycle, `agent-definitions.md` for the directory structure, `quickstart.md` for end-to-end workflow) already cover the same ground in a more accessible format. Rewriting three separate reference docs would duplicate that content and create a maintenance burden.

The `docs/reference/build-phase/launch-overrides.md` file is retained because the `LaunchOverrides` model is unchanged by the simplification change and is not covered by the getting-started docs.

### Self-contained README rewrite rather than link-out

Rewrite the README's agent-definition section (~180 lines) as a self-contained walkthrough of the new layout with inline code examples, rather than replacing it with a brief pointer to the docs site.

Why this over a short link: the README is the first thing most developers read; a GitHub repo viewer may not follow external doc links. The README should give enough context to understand the structure and start using it without leaving the page.

### Coordinate LLM context file updates in the same change

Update `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` in the same change rather than deferring them.

Why: these files are read by AI agents working in this repo. Stale references to the old model cause AI agents to generate code with old paths and terms. Fixing them in the same change prevents a window where docs are correct but AI context is wrong.

### Preserve launch-overrides.md in the build-phase reference

`docs/reference/build-phase/launch-overrides.md` describes the `LaunchOverrides` model which was not affected by the agent-definition simplification. It remains valid and is not duplicated in the getting-started docs.

## Risks / Trade-offs

- [External bookmarks to deleted pages will 404] → Accept this; the docs site is young enough that bookmark breakage is minimal. The getting-started section is the replacement destination.
- [README agent-definition section may drift from getting-started docs] → Keep the README focused on structure overview and examples; reference the docs site for full details at the end of the section.
- [LLM context files may become stale again on future changes] → This is inherent to the approach of embedding architecture descriptions in context files. No mitigation beyond the existing convention of updating them alongside changes.
