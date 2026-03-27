## Context

The current reusable agent-definition model spreads one logical launch target across multiple layers: tool adapters, checked-in tool config profiles, local credential profiles, declarative brain recipes, optional blueprints, and role packages. In practice this creates three categories of confusion:

1. Too many unrelated things are called "config", even though they have different lifetimes and meanings.
2. Several user-visible `name` fields are duplicated or decorative rather than authoritative.
3. The reusable definition layer leaks launch-time managed-agent identity concerns through recipe-owned `default_agent_name`.

The design must preserve one important capability from the current system: the same tool can support multiple checked-in runtime setups and multiple local credential/auth bundles independently. The simplification must therefore reduce naming and layering without collapsing setup and auth into one inseparable axis.

This change is intentionally breaking. Repository guidance already prefers clarity and forward progress over backward-compatibility shims for unstable development.

## Goals / Non-Goals

**Goals:**

- Replace recipe plus blueprint layering with one path-derived preset model.
- Remove duplicated inline identity fields from reusable agent-definition files.
- Rename the checked-in tool input bundle away from generic "config" terminology.
- Keep tool `setup` and tool `auth` as independent per-tool selection axes.
- Make preset schemas minimal and move non-core extensibility into `extra`.
- Keep launch-time managed-agent identity (`agent_name`, `agent_id`) separate from reusable preset metadata.

**Non-Goals:**

- Changing the underlying tmux-backed runtime identity contract in this change.
- Collapsing setup and auth into one combined profile.
- Adding backward-compat parsing for legacy recipe and blueprint files beyond what is minimally needed for a one-shot repo migration.
- Redesigning tool-adapter projection semantics beyond relocating and renaming their source-of-truth paths.

## Decisions

### Use one path-derived preset layer

The new reusable launch target is a preset stored at `agents/roles/<role>/presets/<tool>/<setup>.yaml`.

The preset path derives:

- role
- tool
- setup

The preset file contains only data that cannot be derived from path:

- `skills`
- optional default `auth`
- optional `launch`
- optional `mailbox`
- optional `extra`

This removes duplicated `name`, `role`, and `tool` fields from reusable definitions.

Why this over keeping recipe plus blueprint with renamed fields:

- Renaming alone would still leave two reusable definition files for one logical target.
- Path-derived identity makes uniqueness obvious: the filesystem path is the preset identifier.
- The selector model already trends this way; current native launch resolution derives role and recipe from selector structure rather than needing blueprint names.

### Separate tool-owned setup and auth namespaces

Each tool will own its reusable inputs under:

- `agents/tools/<tool>/adapter.yaml`
- `agents/tools/<tool>/setups/<setup>/...`
- `agents/tools/<tool>/auth/<auth>/...`

`setup` means the checked-in, secret-free files projected into a generated runtime home. `auth` means the local credential bundle and auth env material used for the launch. The generated runtime home remains the runtime output directory and is not renamed.

Why this over one combined profile namespace:

- The same tool must support multiple setup shapes and multiple credentials independently.
- Combining them would either duplicate identical setup content across auth variants or force awkward profile composition later.
- `setup` and `auth` are clearer user-facing terms than `config_profile` and `credential_profile`.

### Remove recipe-owned default managed-agent identity

Reusable preset files will not carry `default_agent_name`. Managed-agent naming is a launch-time concern because uniqueness depends on runtime scope, not on preset authorship.

Launch-time rules stay separate:

- operators may pass `agent_name` and optional `agent_id`
- runtime may continue its current fallback derivation when launch-time identity is omitted

Why this over keeping a preset-owned default name:

- A build-time default name blurs preset identity with live managed-agent identity.
- The same preset may be launched multiple times with different operational identities.
- Keeping identity at launch time makes uniqueness scope explicit instead of implicit.

### Keep the core schema minimal and put non-core data under `extra`

Preset schemas will be strict about top-level core fields and provide `extra` as the only general extension surface for secret-free subsystem-specific metadata.

Why this over keeping placeholder top-level sections:

- It reduces schema ballast and false promises about supported behavior.
- It matches the stated design principle of not pre-allocating unused extension points.
- It makes future additions explicit rather than silently normalized as first-class concepts.

### Do a one-shot repository migration

This change will migrate tracked fixtures, docs, loader logic, and selectors in one breaking cut rather than supporting old and new reusable-definition trees in parallel.

Why this over a compatibility bridge:

- The repository is still unstable and explicitly allows breaking changes.
- Dual-format support would preserve the current conceptual sprawl while adding more code and tests.
- A single migration keeps the implementation and docs coherent.

## Risks / Trade-offs

- [Large fixture-tree churn] -> Update fixtures, docs, and tests in one focused migration and keep the path mapping explicit in the migration notes.
- [Path-derived identity makes renames more significant] -> Treat preset path as the canonical reusable identifier and document that moving or renaming a preset is a contract change.
- [Auth override semantics could become unclear] -> Define a simple rule: launch-time auth override wins; otherwise use preset default auth; manifest always records the effective auth actually used.
- [Existing blueprint-only metadata may not fit the new core schema] -> Move non-core metadata into `extra` and only promote it to first-class schema when there is sustained present-tense usage.
- [Selector resolution may become ambiguous for non-default setups] -> Keep the common selector path simple (`<role>` plus provider resolves `<setup>=default`) and require explicit path-like selectors for non-default setup variants.

## Migration Plan

1. Introduce the new canonical tree under `agents/tools/`, `agents/roles/<role>/presets/`, and `agents/skills/`.
2. Migrate tracked fixtures and demo-owned reusable definitions from recipe/blueprint files into presets plus tool setup/auth directories.
3. Update build and launch loaders to resolve presets, setup bundles, and auth bundles from the new tree.
4. Remove recipe- and blueprint-specific parsing, docs, and tests once the migrated tree is live.
5. Update fixture READMEs and migration notes to document the new naming and scope rules.

Rollback strategy: revert the migration commit set as one unit. This change intentionally does not define a mixed legacy/new steady state.

## Open Questions

- Should path-like `--agents` selectors accept only explicit preset file paths, or also a shorthand such as `<role>/<setup>` when provider already determines tool?
- Should unknown top-level preset fields be rejected outright once `extra` exists, or tolerated temporarily during the migration window with a deprecation error path?
- Should existing blueprint gateway defaults move directly into `extra.gateway`, or should gateway attach depend entirely on explicit launch-time options in this change?
