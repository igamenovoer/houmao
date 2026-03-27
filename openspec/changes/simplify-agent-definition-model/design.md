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
- Introduce a stable canonical parsed model between the user-facing `agents/` source tree and downstream build/launch consumers.
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
- Introducing a second checked-in normalized filesystem tree as the primary downstream contract.

## Decisions

### Insert a parser-owned canonical model boundary

Treat the `agents/` tree as a user-facing source language, not as the downstream construction and launch contract.

The new architecture is:

1. user-facing source files under `agents/`
2. one parser layer for the supported source layout
3. one canonical in-process parsed model
4. selector resolution producing one resolved launch/build specification
5. downstream builder and runtime consuming only that canonical resolved data

The canonical parsed model is the stable internal contract for downstream code. It captures semantic agent-definition data such as:

- role packages
- tool adapters
- setup bundles
- auth bundles
- presets
- launch settings
- mailbox settings
- supported `extra` metadata

The primary contract is in-process value objects and dataclasses, not a second checked-in filesystem format. The system MAY later emit a derived serialized form for debugging or caching, but such emitted data is not user-authored and is not the stability boundary for downstream code.

Why this over letting downstream code read source files directly:

- It prevents build and launch code from depending on source-layout details.
- Future user-facing format changes can be handled by adding a new parser or converter while preserving downstream contracts.
- It avoids creating a second user-facing config surface just to normalize the first one.

### Use one path-derived preset layer

The user-facing source layout stores presets at `agents/roles/<role>/presets/<tool>/<setup>.yaml`.

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

Preset loaders reject unknown top-level fields from day one. `extra` is the only open-ended extension surface, and preserved blueprint-era gateway defaults live under `extra.gateway` rather than as a new core preset field.

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

The parser resolves these source directories into canonical setup/auth definitions before downstream construction logic sees them.

### Remove recipe-owned default managed-agent identity

Reusable preset files will not carry `default_agent_name`. Managed-agent naming is a launch-time concern because uniqueness depends on runtime scope, not on preset authorship.

Launch-time rules stay separate:

- preset-backed launch surfaces keep `--agent-name` optional and `--agent-id` optional
- operators may pass `agent_name` and optional `agent_id`
- when `agent_name` is omitted, runtime derives the fallback logical managed-agent identity from tool plus role via the current runtime auto-name path
- operators who need multiple distinct concurrently managed logical agents for the same preset must provide explicit `--agent-name` values

Why this over keeping a preset-owned default name:

- A build-time default name blurs preset identity with live managed-agent identity.
- The same preset may be launched multiple times with different operational identities.
- Keeping identity at launch time makes uniqueness scope explicit instead of implicit.

### Define the preset `launch` schema explicitly

Preset `launch` is one optional object with two optional fields:

- `prompt_mode`
- `overrides`

`prompt_mode` carries the current operator-prompt policy (`interactive` or `unattended`). `overrides` reuses the current `LaunchOverrides` shape, meaning optional `args` and optional `tool_params`.

Both fields are forwarded through build and local launch so preset-authored launch behavior stays in one place instead of being split between core schema and `extra`.

Why this over splitting launch-affecting data across multiple places:

- It keeps all preset-owned launch behavior under one stable key.
- It reuses the current launch-overrides model instead of inventing a second ad hoc override shape.
- It keeps `extra` for non-core metadata rather than for routine launch behavior.

### Keep the core schema minimal and put non-core data under `extra`

Preset schemas will be strict about top-level core fields and provide `extra` as the only general extension surface for secret-free subsystem-specific metadata.

Why this over keeping placeholder top-level sections:

- It reduces schema ballast and false promises about supported behavior.
- It matches the stated design principle of not pre-allocating unused extension points.
- It makes future additions explicit rather than silently normalized as first-class concepts.

### Keep selector grammar simple and explicit

Preset-backed `--agents` resolution supports exactly two selector forms:

- bare role name `<role>` together with provider-derived tool selection, which resolves `setup=default`
- explicit preset file path

The system does not support a `<role>/<setup>` shorthand in this change.

Why this over adding a hybrid shorthand immediately:

- It preserves the current clean name-based versus path-like distinction in the native resolver.
- It avoids introducing ambiguous slash-containing selectors.
- It keeps the common path short while making non-default variants explicit.

The selector resolver operates on the canonical parsed catalog rather than inspecting source files directly inside downstream launch code.

### Bump the resolved manifest to schema version 3

The resolved brain manifest moves from schema version 2 to schema version 3 in this change because the selected reusable-definition inputs change materially from legacy config-profile / credential-profile fields to `preset_path`, `setup`, and effective `auth`.

The implementation updates include:

- writing schema version 3 manifests
- updating manifest loading/parsing to accept the new version
- regenerating the checked-in JSON schema artifacts that validate the manifest structure

Why this over leaving the manifest version unchanged:

- The loader currently hard-requires schema version 2.
- The changed field set is a real compatibility boundary, not a cosmetic rename.
- A version bump keeps build outputs and loaders honest during the one-shot migration.

### Keep downstream consumers source-format-agnostic

Native launch resolution, brain construction, and runtime startup consume only canonical parsed definitions or derived resolved launch/build specifications.

Concretely:

- selector resolution reads from the canonical parsed catalog
- brain construction consumes a resolved build specification rather than source-facing preset/recipe payloads
- runtime startup consumes manifest and launch-time inputs without knowing the original user-facing source layout

Why this matters:

- `agents/` layout changes become parser work rather than builder/runtime refactors
- tests can separate source parsing from downstream behavior
- the simplified user-facing model stays free to evolve without re-coupling downstream code to its exact file structure

### Do a one-shot repository migration

This change will migrate tracked fixtures, docs, loader logic, and selectors in one breaking cut rather than supporting old and new reusable-definition trees in parallel.

Why this over a compatibility bridge:

- The repository is still unstable and explicitly allows breaking changes.
- Dual-format support would preserve the current conceptual sprawl while adding more code and tests.
- A single migration keeps the implementation and docs coherent.

## Risks / Trade-offs

- [Large fixture-tree churn] -> Update fixtures, docs, and tests in one focused migration and keep the path mapping explicit in the migration notes.
- [Path-derived identity makes renames more significant] -> Treat preset path as the canonical reusable identifier and document that moving or renaming a preset is a contract change.
- [Canonical parsed model could accidentally mirror source layout too closely] -> Keep the parsed model semantic and downstream-oriented; avoid carrying decorative source-only fields into the canonical contract.
- [Auth override semantics could become unclear] -> Define a simple rule: launch-time auth override wins; otherwise use preset default auth; manifest always records the effective auth actually used.
- [Existing blueprint-only metadata may not fit the new core schema] -> Move non-core metadata into `extra` and only promote it to first-class schema when there is sustained present-tense usage.
- [Selector resolution may become ambiguous for non-default setups] -> Keep the common selector path simple (`<role>` plus provider resolves `<setup>=default`) and require explicit preset file paths for non-default setup variants.
- [Auto-derived managed-agent identity can be reused accidentally] -> Preserve optional `--agent-name` and require operators to provide it when they need multiple distinct concurrently managed logical agents from the same preset.

## Migration Plan

1. Introduce the new user-facing source tree under `agents/tools/`, `agents/roles/<role>/presets/`, and `agents/skills/`.
2. Define the parser for that source layout and the canonical parsed data model it produces.
3. Migrate tracked fixtures and demo-owned reusable definitions from recipe/blueprint files into presets plus tool setup/auth directories.
4. Update selector resolution, builder inputs, and launch surfaces to consume canonical parsed definitions rather than source-shaped files directly.
5. Remove recipe- and blueprint-specific parsing, docs, and tests once the migrated tree is live.
6. Update fixture READMEs and migration notes to document the new naming, scope, and parser-boundary rules.

Rollback strategy: revert the migration commit set as one unit. This change intentionally does not define a mixed legacy/new steady state.
