# Validate Execplan

## Preconditions

- Generated `execplan/` exists.
- User wants inspection before execution or after `update-execplan`.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/`

## Actions

Check shape:
- `execplan/manifest.toml` exists.
- `execplan/manifest.toml` is parseable and, when it indexes artifact paths, every indexed path exists.
- `execplan/manifest.toml` identifies generated-source posture, plan revision, artifact paths, artifact kinds or purposes, and any intentional omission of default layers.
- `execplan/specs/` exists.
- `execplan/skills/` exists.
- `execplan/agents/` exists.
- `execplan/harness/` exists.
- `execplan/docs/` exists.
- optional specs for objective, collaboration, communication, state, workspace, and participants exist when generated skills, agent bindings, or harness commands depend on those concerns.

Check generated skills:
- generated skills under `execplan/skills/*/SKILL.md` have valid skill frontmatter.
- generated on-event and on-tick skills state their trigger, role owner, bounded procedure, and output or handoff posture.

Check agent bindings:
- generated participant contracts separate role templates or role descriptions, stable participant instances, and concrete Houmao agent bindings.
- concrete agent bindings under `execplan/agents/` identify their intended participant or role.
- concrete agent bindings identify prompt source, installed generated skills, maintained support skills, skill installation mode, memo seed policy, and workspace or launch policy when the execplan defines those concepts.

Check runtime state and records:
- durable-state plans include loop-local contracts for plan metadata, process state, handoffs or exchanges, communication payload lifecycle, operator intent events, and generic events, or document an accepted equivalent.
- task-specific records, evidence models, scoring models, and domain tables appear only when introduced by intention source or generated clarification output.
- generated record contracts exist for structured bookkeeping that the harness or skills claim to apply.
- state contracts do not require a particular backend unless the generated loop explicitly selects it.

Check workspace contracts:
- workspace setup contracts route workspace planning or creation through `houmao-utils-workspace-mgr` when the requested layout is a supported Houmao workspace flavor.
- default workspace policy is `in-repo` plus any explicitly listed loop bookkeeping directories, unless intention source chooses a different supported flavor or a custom operator-owned workspace.
- workspace contracts identify launch cwd, per-agent work roots, per-agent note or knowledge paths, writable temporary or artifact paths, shared resources, and read/write rules when those facts apply.

Check run artifacts:
- durable-execution plans define a run artifact layout such as `runs/<run-id>/` or an explicit equivalent.
- the run artifact layout preserves structured payloads, rendered outputs, send or reply responses, records, state files, logs, evidence, and operator notes when the loop claims those artifacts exist.

Check mail-driven communication contracts:
- mail-driven plans route mailbox setup, ordinary mail operations, gateway-notified rounds, managed-agent communication routing, and gateway lifecycle to maintained Houmao skills rather than generated platform mechanics.
- generated agent bindings for mail-driven participants include required maintained mail support skills for the participant's responsibilities.
- generated communication registries under `execplan/specs/comms/` connect schema ids, payload formats, and renderers coherently when the loop is mail-driven.
- mail-driven plans include `execplan/specs/comms/templates.toml` unless intention source defines an equivalent registry.
- every ordinary generated mail family indexed in `templates.toml` identifies a schema id, schema path, renderer path, payload format, and reply expectation when a reply is expected.
- generated templated mail schemas include a common envelope or document the accepted alternative, covering `schema_id`, `schema_version`, `payload_id`, `kind`, `run_id`, `plan_revision`, exchange or handoff id, and `context`.
- generated request payloads identify `requested_reply_schema_id` or an equivalent reply-family link when a structured reply is expected.
- generated mail renderers include a fenced `houmao-email-metadata` block, a human-readable `Context` section, template-specific sections, and an explicit reply request section when the sender expects a reply.
- mail-driven plans include `freeform-notice` and `ack` families or document equivalent accepted families.
- generated payload lifecycle contracts exist when runtime state records templated mail, and they do not treat harness lifecycle commands as mailbox delivery.
- generated mail-received on-event skills identify the trigger schema id or message family, role owner, bounded procedure, reply behavior, archive-after-success behavior, and stopping point.
- aggregation, scheduling, timeout handling, reconciliation, and completion checks are assigned to on-tick skills when they do not belong to one received-mail event.

Check parseability and source posture:
- generated JSON schemas under `execplan/specs/comms/` or `execplan/specs/collab/records/` parse as JSON when present.
- generated harness commands or docs expose the loop's dynamic lookup and data-model mechanics when skills depend on harness lookup, schema validation, rendering, query, or controlled record application.
- harness output intended for agents uses a structured envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings, or documents an accepted equivalent.
- harness explanation surfaces expose structured rationale from generated contracts when generated skills rely on explanation behavior.
- generated docs do not claim to be source authority.
- intention files remain under `intention/`, not inside generated `execplan/`.

Harness rule:
- If a generated harness provides a validation command, run that command and prefer its machine-readable output.

## Output

Report:
- validation pass or fail,
- missing required files or directories,
- parse or link failures in manifest, TOML, JSON schemas, schema/render registries, or agent bindings,
- stale or ambiguous generated-source markers,
- whether the plan appears ready for execution subskills.

## Constraints

- Do not fix validation failures unless the user asked for repair or `update-execplan`.
- Do not fail only because `<loop-dir>/adrs/` is absent.
- Do not validate domain-specific fields unless the intention source introduced that domain.
