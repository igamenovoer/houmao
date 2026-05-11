# Execplan Contract Intent

This note records the intended direction for generated v5 execplans. It is not a validator and is not part of runtime skill routing.

## Contract Layers

A generated execplan should separate these concerns:

- `manifest.toml`: artifact index, plan identity, generated-source posture, and revision metadata.
- `specs/`: machine-readable loop contracts for objectives, participants, collaboration policy, communication payloads, state, and workspace behavior.
- `skills/`: generated participant-facing operation skills, event handlers, and shared utility skills.
- `agents/`: concrete Houmao agent bindings that map participants to prompt sources, installed skills, workdirs, and initialization policy.
- `harness/`: plan-local deterministic helpers for data-model management, validation, query, rendering, record application, dynamic information lookup, and other loop-local mechanics.
- `docs/`: generated human support views that explain the generated contracts without becoming source authority.

The top-level v5 skill currently requires only the broad layout. Future improvements should tighten validation by adding explicit checks for artifact coverage, parseability, schema/render pairing, agent binding fields, and harness command behavior.

## Source Boundary

`intention/` is the editable source of truth. `execplan/` is regenerated output.

When generated material needs richer policy than the current intention states, the generator should preserve an explicit unresolved entry instead of copying assumptions from a domain-specific example.

## Reference Shape

A mature generated loop plan is useful as a reference for the depth of a complete execplan, not as a global template. Useful reference traits include:

- structured TOML contracts under `specs/`;
- schema-validated communication and record payloads with Markdown renderers when human-readable output is needed;
- SQLite-backed state contracts and migrations when runtime state is needed;
- participant role templates separated from concrete agent bindings;
- generated skills scoped to role events, plus tick skills for periodic or scheduler-like responsibilities;
- a narrow per-loop harness rather than new Houmao core commands;
- generated Markdown metadata marking generated files.

See `reference-execplan-patterns.md` for a more detailed maintainer-oriented reading of the generic pattern.

Do not make any reference package's domain, topology, toolchain, evidence policy, or scheduling policy part of the global v5 contract. Those details belong in the loop intention and the generated per-loop execplan.

## Validation Direction

Validation should grow from shape checks toward contract checks:

- parse `manifest.toml` and confirm every indexed artifact exists;
- verify generated Markdown markers where generated docs are expected;
- parse TOML contracts and JSON schemas;
- validate skill frontmatter for every generated skill;
- validate generated communication and record registries connect schema ids, payload formats, and renderers coherently;
- validate agent configs include participant identity, prompt source, installed skills, and workspace policy;
- run harness self-checks when present;
- report stale or ambiguous generated-source metadata;
- keep domain-specific validation opt-in and derived from the loop source.
