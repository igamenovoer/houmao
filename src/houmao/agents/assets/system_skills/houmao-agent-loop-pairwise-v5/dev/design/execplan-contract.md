# Execplan Contract Intent

This note records the intended direction for generated execplans. It is not a validator and is not part of runtime skill routing.

## Contract Layers

A generated execplan should separate these concerns:

- `manifest.toml`: artifact index, plan identity, generated-source posture, and revision metadata.
- `specs/`: machine-readable loop contracts for objectives, participants, collaboration policy, communication payloads, state, and workspace behavior.
- `skills/`: generated participant-facing operation skills, event handlers, and shared utility skills.
- `agents/`: concrete Houmao agent bindings that map participants to prompt sources, installed skills, workdirs, and initialization policy.
- `harness/`: plan-local deterministic helpers for data-model management, validation, query, rendering, record application, dynamic information lookup, and other loop-local mechanics.
- `docs/`: generated human support views that explain the generated contracts without becoming source authority.

The top-level skill currently requires only the broad layout. Future improvements should tighten validation by adding explicit checks for artifact coverage, parseability, schema/render pairing, agent binding fields, and harness command behavior.

## Communication Default Contract

Ordinary cross-agent participant handoffs default to Houmao mail unless the intention source explicitly selects a non-mail mechanism. The generator should not preserve a design gap that asks "should participants use mail?" when the source is silent; the useful questions are loop-specific: which roles communicate, which message families exist, which payload fields are required, which replies are expected, and which state or records change.

Mail-driven execplans should keep semantic ownership in generated material and mechanical ownership in maintained Houmao skills. Generated specs define routes, message families, schemas, renderers, reply links, lifecycle records, and event/tick behavior. Maintained skills own mailbox setup, ordinary mail operations, gateway-notified mail rounds, managed-agent communication routing, and gateway posture.

The default generated communication package is:

```text
execplan/specs/comms/
  comms-overview.md
  templates.toml
  schemas/
    freeform-notice.schema.json
    ack.schema.json
    <message-family>.schema.json
  renderers/
    freeform-notice.md.j2
    ack.md.j2
    <message-family>.md.j2
```

`templates.toml` is the registry that lets generated skills and harness commands resolve a short template name or schema id to the schema path, renderer path, payload format, route constraints, and expected reply family. TOML is the default structured payload format; Markdown is the default rendered mail surface.

Templated payloads should carry a common envelope: `schema_id`, `schema_version`, `payload_id`, `kind`, `run_id`, `plan_revision`, an exchange or handoff id, and `context`. Requests that expect structured replies should carry `requested_reply_schema_id` or an explicit equivalent. Rendered mail should include a fenced `houmao-email-metadata` block, a `Context` section, template-specific human-readable sections, and an explicit reply request section when a reply is expected.

When runtime state exists, the harness may expose `email schema|validate|render|apply|query` commands for schema lookup, TOML validation, Markdown rendering, lifecycle record application, and lifecycle query. These commands record loop-local facts; they are not mailbox delivery. Actual send, read, reply, archive, mailbox binding, and gateway behavior stay delegated to maintained Houmao mail support.

Generated mail-received skills should be one-event handlers keyed by schema id or message family. They should validate or interpret the received payload, perform one bounded role-owned action, send required replies through maintained mail support, archive only after success, then stop. Aggregation, scheduling, timeout handling, reconciliation, and completion checks belong in on-tick skills when they do not conceptually belong to one received-mail event.

## Source Boundary

`intention/` is the editable source of truth. `execplan/` is regenerated output.

When generated material needs richer policy than the current intention states, the generator should preserve an explicit unresolved entry instead of copying assumptions from a domain-specific example.

## Reference Shape

A mature generated loop plan is useful as a reference for the depth of a complete execplan, not as a global template. Useful reference traits include:

- structured TOML contracts under `specs/`;
- schema-validated communication and record payloads with Markdown renderers when human-readable output is needed;
- compact state contracts when runtime state is needed;
- participant role templates separated from concrete agent bindings;
- generated skills scoped to role events, plus tick skills for periodic or scheduler-like responsibilities;
- a narrow per-loop harness rather than new Houmao core commands;
- workspace setup routed through `houmao-utils-workspace-mgr`, defaulting to the standard in-repo workspace flavor with explicit loop bookkeeping directories when needed;
- generated Markdown metadata marking generated files.

See `reference-execplan-patterns.md` for a more detailed maintainer-oriented reading of the generic pattern.

Do not make any reference package's domain, topology, toolchain, evidence policy, or scheduling policy part of the global contract. Those details belong in the loop intention and the generated per-loop execplan.

Do not make a reference package's exact participant topology, domain message-family names, evidence fields, or required state backend global. The reusable communication defaults are mail as the ordinary participant transport, schema-validated TOML payloads, Markdown renderers, a registry, explicit reply links, payload lifecycle records when state exists, and maintained Houmao mail-skill delegation.

## Validation Direction

Validation should grow from shape checks toward contract checks:

- parse `manifest.toml` and confirm every indexed artifact exists;
- verify generated Markdown markers where generated docs are expected;
- parse TOML contracts and JSON schemas;
- validate skill frontmatter for every generated skill;
- validate generated communication and record registries connect schema ids, payload formats, and renderers coherently;
- validate agent configs include participant identity, prompt source, installed skills, and workspace policy;
- validate supported workspace setup routes through `houmao-utils-workspace-mgr` rather than generated ad hoc worktree mechanics;
- run harness self-checks when present;
- report stale or ambiguous generated-source metadata;
- keep domain-specific validation opt-in and derived from the loop source.
