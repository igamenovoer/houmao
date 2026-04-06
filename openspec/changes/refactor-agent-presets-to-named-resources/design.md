## Context

Today Houmao treats low-level presets as path-derived files under `agents/roles/<role>/presets/<tool>/<setup>.yaml`. That decision shows up in four places at once:

- the low-level CLI nests preset operations under `project agents roles presets`,
- the parser derives `role`, `tool`, and `setup` from the preset path,
- bare role launch resolves `roles/<role>/presets/<tool>/default.yaml`,
- tracked docs, demos, and fixtures teach the same nested shape.

This makes the `roles` resource misleading. A role is effectively just `system-prompt.md`, while the launch binding that selects tool, setup, auth, and skills is the preset. The current model therefore hides the real resource boundary behind directory nesting.

This refactor intentionally changes the resource model rather than adding another alias on top of the old one. The repository is under active development and does not need a long-lived compatibility layer for the old preset layout.

## Goals / Non-Goals

**Goals:**
- Make presets a first-class named resource at both the CLI and storage levels.
- Keep roles focused on prompt ownership only.
- Preserve the simple bare-role launch flow for the common default case.
- Remove low-level convenience generation that no longer fits the prompt-only role model.
- Update repo-owned catalog projection, docs, demos, and fixtures to one consistent preset model.

**Non-Goals:**
- Add the `houmao-manage-agent-definition` packaged skill in this change.
- Preserve backward-compatible read/write support for role-scoped preset paths.
- Introduce a second shorthand selector family for launch beyond bare role and explicit preset path.
- Redesign auth bundles, setup bundles, or specialist semantics beyond the preset identity changes required here.

## Decisions

### 1. Presets become named top-level files under `agents/presets/`

The canonical filesystem-backed preset layout becomes:

```text
agents/
├── roles/<role>/system-prompt.md
├── presets/<preset>.yaml
└── tools/<tool>/...
```

Each preset file stores:

```yaml
role: researcher
tool: codex
setup: default
skills:
  - notes
auth: yunwu-openai
launch:
  prompt_mode: unattended
mailbox: null
extra: {}
```

The preset name is derived from the filename stem and is not duplicated inside the file.

Rationale:
- The CLI can now expose presets honestly as their own resource.
- A preset can be referenced, inspected, and updated without pretending that its primary identity is a role subtree path.
- The file content now carries the semantic relationship that the parser and catalog already need.

Alternatives considered:
- Keep `agents/roles/<role>/presets/...` storage and only add a top-level CLI alias. Rejected because the old path-derived identity would still leak through docs, parser rules, and runtime selectors.
- Add a top-level preset name while also storing `name:` inside YAML. Rejected because filename and inline identity can drift.

### 2. `project agents roles` becomes prompt-only and `roles scaffold` is removed

The low-level project CLI becomes:

```text
houmao-mgr project agents
├── roles
│   ├── list
│   ├── get --name <role> [--include-prompt]
│   ├── init --name <role> [--system-prompt <text> | --system-prompt-file <path>]
│   ├── set --name <role> [--system-prompt <text> | --system-prompt-file <path> | --clear-system-prompt]
│   └── remove --name <role>
├── presets
│   ├── list [--role <role>] [--tool <tool>]
│   ├── get --name <preset>
│   ├── add --name <preset> --role <role> --tool <tool> [--setup <setup>] [--auth <bundle>] [--skill <name> ...] [--prompt-mode unattended|as_is]
│   ├── set --name <preset> [--role <role>] [--tool <tool>] [--setup <setup>] [--auth <bundle> | --clear-auth] [--add-skill <name> ...] [--remove-skill <name> ...] [--clear-skills] [--prompt-mode unattended|as_is | --clear-prompt-mode]
│   └── remove --name <preset>
└── tools
    └── <tool> ...
```

`project agents roles scaffold` is removed entirely. Low-level authoring should no longer create placeholder setup/auth/skill trees as a side effect of role creation.

Rationale:
- The command tree now matches the data model.
- Prompt-only roles are easier to explain and inspect.
- Placeholder generation belongs in higher-level authoring flows, not in a low-level declarative surface.

Alternatives considered:
- Keep `roles scaffold` as a convenience alias that also creates a preset. Rejected because it keeps `roles` semantically overloaded.
- Keep nested `roles presets ...`. Rejected because the whole point of the refactor is to stop presenting presets as subordinate role internals.

### 3. Parser and catalog switch from path-derived preset identity to named preset identity

`parse_agent_preset()` will parse `role`, `tool`, and `setup` from file content, and it will derive only the preset name from the file path. Unsupported top-level fields remain rejected, but the supported preset schema expands to include required `role`, `tool`, and `setup`.

The catalog schema will treat preset name as a first-class identity. The `presets` table gains a unique preset name and retains uniqueness on `(role_id, tool, setup_profile_id)` so bare role launch remains deterministic. Compatibility projection writes preset files under `agents/presets/<name>.yaml`.

Rationale:
- Parsing should no longer depend on directory nesting.
- Named preset identity must exist in the catalog to keep projection, inspection, and specialist relationships stable.
- Keeping `(role, tool, setup)` unique preserves one default preset candidate for the bare-role launch path.

Alternatives considered:
- Allow multiple preset names for the same `(role, tool, setup)` tuple. Rejected because bare role launch would become ambiguous.
- Continue projecting `roles/<role>/presets/...` from the catalog while storing names internally. Rejected because it preserves the misleading public tree.

### 4. Launch/build keep simple selectors while moving to named preset resources

This change keeps the public selector contract intentionally narrow:

- `houmao-mgr agents launch --agents <role> --provider <provider>` still means "launch the default setup for this role on this tool lane".
- `houmao-mgr agents launch --agents <path>` still accepts explicit preset file paths, now typically `agents/presets/<name>.yaml`.
- `houmao-mgr brains build --preset <value>` accepts either an explicit preset path or a bare preset name, because the flag already names the preset resource directly.

Bare role launch resolves by finding the unique preset where:

- `preset.role == <role>`
- `preset.tool == <provider-derived tool>`
- `preset.setup == default`

Rationale:
- Existing operator muscle memory for bare role launch survives.
- The explicit preset path form stays unambiguous.
- `brains build --preset` can naturally accept a bare preset name because that command already declares preset intent explicitly.

Alternatives considered:
- Make bare `--agents <value>` prefer preset names over roles. Rejected because it would make role selection ambiguous.
- Add a new launch-only selector syntax such as `preset:<name>`. Rejected as extra surface area for this refactor.

### 5. This is a direct repository rewrite, not a dual-layout migration layer

The change updates repo-owned docs, fixtures, tests, demos, parser rules, and projection code to the new preset model in one pass. The runtime and low-level project CLI will stop treating `roles/<role>/presets/...` as a supported canonical path.

For project-local overlays created during development, the expected migration path is to rewrite or recreate preset files in the new form rather than keeping a long-term dual parser or bidirectional compatibility projection.

Rationale:
- The repository explicitly allows breaking changes during active development.
- A dual-layout compatibility layer would complicate parser logic, catalog projection, tests, and docs for limited long-term value.

Alternatives considered:
- Read both old and new layouts indefinitely. Rejected because it undermines the refactor and prolongs the misleading model.

## Risks / Trade-offs

- [Wide spec and fixture churn] → Limit the change to one new canonical model and update repo-owned fixtures/docs in the same change so there is only one supported story afterward.
- [Catalog schema drift during refactor] → Bump the catalog schema intentionally, update projection code and read paths together, and cover the new schema with unit tests around preset creation, inspection, and specialist projection.
- [Bare role launch ambiguity] → Keep `(role, tool, setup)` unique and fail clearly if future code ever encounters duplicate default candidates.
- [Operator confusion during transition] → Update CLI help, getting-started docs, and CLI reference in the same change; remove `roles scaffold` rather than leaving a deprecated command that encodes the old mental model.
- [Unmigrated local overlays break] → Prefer explicit errors that point to `agents/presets/<name>.yaml` and the new `project agents presets ...` commands over silent partial compatibility.

## Migration Plan

1. Add the new named preset schema and parser support.
2. Update catalog schema/projection and project-local write paths to persist and project named presets.
3. Replace `project agents roles presets ...` with `project agents presets ...` and remove `roles scaffold`.
4. Update launch/build selector resolution for named presets and default role resolution.
5. Rewrite repo-owned fixtures, demos, and docs to the new preset layout.
6. Remove remaining repository references to `roles/<role>/presets/<tool>/<setup>.yaml` from supported surfaces.

Rollback strategy:
- Until implementation is merged, discard the refactor.
- After merge, rollback means reverting the change set; this design does not preserve a runtime compatibility bridge between the two layouts.

## Open Questions

- None. The main trade-offs for storage, CLI shape, selector semantics, and compatibility posture are intentionally decided in this change.
