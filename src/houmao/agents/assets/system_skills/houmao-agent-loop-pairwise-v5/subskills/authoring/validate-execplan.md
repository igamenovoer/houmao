# Validate Execplan

## Read First

- `../reference/scaffold-surface.md`
- `../reference/generation-pipeline.md`
- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- Generated `execplan/` exists.
- User wants inspection before execution or after `update-execplan`.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/`

## Actions

Check shape:
- `execplan/manifest.toml` exists at the canonical scaffold-owned path used by `execplan-shell` or `execplan-stepwise-shell`.
- `execplan/manifest.toml` is parseable and, when it indexes artifact paths, every indexed path exists.
- `execplan/manifest.toml` identifies generated-source posture, plan revision, artifact paths, artifact kinds or purposes, and any intentional omission of default layers.
- `execplan/specs/` exists.
- `execplan/skills/` exists.
- `execplan/agents/` exists.
- `execplan/harness/` exists.
- `execplan/docs/` exists.
- optional specs for objective, collaboration, communication, state, workspace, run artifacts, and participants exist when generated skills, agent bindings, or harness commands depend on those concerns.
- generated artifact paths follow the canonical package shape unless an explicit omission or accepted equivalent is recorded in `manifest.toml`, generated docs, or validation notes.
- `execplan/adrs/` is optional; when present, ADR entries are generated-decision records created from the shared ADR path shape and are indexed by the manifest or summarized by final docs.

Check generated artifact directory README files:
- every emitted generated artifact directory includes `README.md`, unless the directory is intentionally omitted or covered by a documented exception.
- each generated artifact directory README uses only these top-level sections after the title:
  - `Purpose`;
  - `Contents`.
- README `Purpose` explains why the directory exists.
- README `Contents` lists generated files or child directories in that directory and briefly states what each one is.
- generated README files do not duplicate schema fields, command semantics, role procedures, binding contracts, manifest rows, or other authoritative details.
- generated README files are orientation only and do not claim source authority.
- simple generated skill directories may omit a local README when they contain only `SKILL.md` and optional `agents/openai.yaml`; `execplan/skills/README.md` must still describe the generated skill collection.

Check staged generation posture:
- generated material records or documents that process specs are the first generated authority when the loop uses staged generation.
- `execplan/specs/collab/collab-overview.md` exists as the canonical process overview.
- `execplan/specs/process.md` does not exist as the canonical process overview; if present, report it as a misplaced generated artifact that should be moved under `specs/collab/`.
- process specs describe phases, events, handoffs or exchanges, tick responsibilities, ownership, terminal posture, recovery posture, and provisional participant, message, state, or record families when those concepts apply.
- process docs include Python-style pseudocode in fenced `python` code blocks, with inline comments that explain conditions, actions, state effects, and stopping points.
- process docs include a high-level Mermaid sequence graph in a fenced `mermaid` code block that shows the main participant/event/handoff flow.
- derived objective, participant, topology, communication, state, record, workspace, run, harness, skill, and agent-binding artifacts do not introduce process semantics that bypass the process specs.
- final docs and final manifest are generated after authoritative artifacts exist, or they document the staged generation snapshot they summarize.
- explicit omissions are reflected in the final manifest, generated docs, or validation notes.

Check generated skills:
- `execplan/skills/README.md` exists and uses only `Purpose` and `Contents`.
- generated skills live as flat skill directories under `execplan/skills/<unique-skill-name>/`.
- generated skills are not loose Markdown files directly under `execplan/skills/`.
- generated skills do not use nested category directories such as `execplan/skills/shared/`, `execplan/skills/on-event/`, `execplan/skills/on-tick/`, or `execplan/skills/operator/`.
- generated skills under `execplan/skills/*/SKILL.md` have valid skill frontmatter.
- generated skill directory names and frontmatter names are unique across the execplan package and suitable for installation into one flat skill namespace.
- generated skill directories with extra generated files beyond `SKILL.md` and optional `agents/openai.yaml` include local README files with only `Purpose` and `Contents`.
- generated on-event and on-tick skills state their trigger, role owner, bounded procedure, and output or handoff posture.
- controllable loops include `execplan/skills/<loop-slug>-operator-control/SKILL.md` or record an accepted equivalent.
- generated operator-control skills identify loop slug, loop dir, manifest path, harness path, agent binding path, supported lifecycle operations, and maintained Houmao support-skill routes.
- generated operator-control support pages, when present, live inside that skill directory rather than under a category directory.
- generated on-tick skills for controllable loops query harness control context and branch between `auto` and `manual` behavior when both modes apply.

Check harness shape:
- generated harness directories include README files with only `Purpose` and `Contents`.
- generated harnesses include `execplan/harness/commands.toml` unless the manifest records an accepted no-code or external harness surface.
- generated harness implementation files live under `execplan/harness/bin/`, `execplan/harness/src/`, or documented equivalent paths indexed by the manifest.
- generated harness command registries refer to generated package artifacts with relative paths, such as `../specs/...` or `../agents/...`, unless a generated contract explicitly defines an external runtime path.
- when generated harness scripts need stable local paths, those paths are either relative symlinks under `execplan/harness/refs/` pointing to authoritative package artifacts, or direct relative paths to the authoritative artifacts when symlinks are unavailable.
- generated harness symlink targets are relative paths, not absolute paths.
- `execplan/harness/schemas/` contains only harness-owned schemas such as command envelopes; communication, record, state, workspace, participant, and objective schemas remain authoritative under `execplan/specs/` and are referenced rather than copied.
- generated harnesses that import `click`, `jinja2`, `jsonschema`, or other non-stdlib libraries declare those libraries and record a dependency posture such as `houmao-env`, `environment-provided`, `local-pip-target`, `pending-local-install`, `unavailable`, or an accepted equivalent.
- generated harnesses that use `.md.j2` renderers declare `jinja2`, harnesses with modular CLI command routing declare `click`, and harnesses with JSON Schema validation declare `jsonschema`.
- dependency posture metadata records the interpreter used for import detection or installation, required packages, version constraints, selected install command when local target support exists, and install diagnostics or pending status.
- generated harness entrypoints that import non-stdlib libraries include import-failure guidance that names the missing dependency and tells the caller to install it into the active harness Python environment or use the Python environment associated with the installed Houmao uv tool.
- generated harness import-failure guidance does not hardcode a uv tool environment path; it points to inspection or refresh commands such as `uv tool list --show-paths --show-python`.
- generated harness authoring notes, validation notes, or README material tell authoring agents to retry failed dependency or interpreter-sensitive harness tests through the Houmao uv-installed environment before treating the failure as a harness implementation bug.
- `execplan/harness/requirements.txt` exists and is manifest-indexed only when dependency posture is `local-pip-target`, `pending-local-install`, or an equivalent caller-managed standalone dependency posture.
- local target requirements include only libraries the harness uses.
- `execplan/harness/vendor/` exists or is explicitly recorded as pending or unavailable when local target posture is selected.
- generated entrypoints prepend the harness-local `vendor/` directory to `sys.path` before importing locally installed libraries when optional standalone local target posture may be used.
- generated harness docs or metadata include the local target command `python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt` or an accepted equivalent only when standalone local target support is claimed.
- generated plans that claim a skill-bundled wheelhouse fallback, `local-wheelhouse-target` posture, `--no-index --find-links <wheelhouse-dir>` fallback, or a skill-owned `assets/harness-wheelhouse/` source are stale or non-conforming.
- generated harnesses do not require installing `click`, `jinja2`, `jsonschema`, or their dependencies into system Python, user site-packages, or the surrounding project environment.
- controllable generated harnesses expose control status and mode lookup commands, or document an accepted equivalent.
- generated harnesses that claim manual mode expose participant-specific manual context with run state, execution mode, participant id, relevant pending mail or handoff refs, allowed actions, and one-pass stop posture.
- generated harnesses record mode changes, pause, resume, stop, override, and recovery as operator intent records when those controls exist.
- generated harnesses do not directly own notifier enable/disable, managed-agent prompting, mailbox delivery, or managed-agent lifecycle mechanics.

Check agent bindings:
- generated agent-binding directories include README files with only `Purpose` and `Contents`.
- generated participant contracts separate role templates or role descriptions, stable participant instances, and concrete Houmao agent bindings.
- concrete agent bindings include `execplan/agents/bindings.toml`.
- concrete agent profile material lives under `execplan/agents/profiles/<agent-id>/`.
- concrete agent bindings under `execplan/agents/` identify their intended participant or role.
- concrete agent bindings identify prompt source, installed generated skills, maintained support skills, skill installation mode, memo seed policy, and workspace or launch policy when the execplan defines those concepts.
- concrete agent bindings reference workspace policy from generated workspace contracts when managed workspaces are required; they do not become the only source of workspace behavior.
- mail-driven bindings include notifier prompt material under `execplan/agents/notifier-prompts/` or document the equivalent prompt source.

Check runtime state and records:
- durable-state plans include loop-local contracts for plan metadata, process state, handoffs or exchanges, communication payload lifecycle, operator intent events, and generic events, or document an accepted equivalent.
- durable-state plans include `execplan/specs/state/README.md` and `execplan/specs/state/state-overview.md`.
- `execplan/specs/state/state-overview.md` describes state authority, state boundaries, minimal entity families, allowed states or transitions, invariants, scheduling queries, and content that state must not store.
- when stable entities and transitions can be expressed as a clear SQL schema, generated bookkeeping defaults to sqlite and includes `execplan/specs/state/schema.sql`.
- sqlite-backed plans treat `schema.sql` as field-level state authority and do not duplicate table definitions in README files.
- JSONL-backed state is accepted only when the plan documents append-only, schema-light, or intentionally denormalized state and includes explicit schemas for every generated JSONL record type.
- generated state does not use unstructured ad hoc state files when sqlite or JSONL plus schema is feasible.
- state records store compact facts and durable refs instead of full mail bodies, rendered Markdown, long rationale, pseudocode, detailed analysis, or documentation content.
- important state transitions are reconstructable from structured records that identify changed entity, new state or decision, actor or source, related mail/evidence/artifact refs, and timestamp.
- active ownership is represented clearly enough for scheduler and recovery queries.
- operator override, pause, prune, stop, repair, and recovery authority is recorded as operator intent events when those controls exist.
- controllable loops distinguish run lifecycle state from execution mode, and do not treat `manual` as equivalent to `paused`.
- controllable loops default initial execution mode to `auto` unless intention source, accepted clarification decisions, or operator-control state selects another mode.
- auto mode is documented as notifier-prompt-driven when the loop is mail-driven.
- manual mode is documented as operator-prompted bounded work with notifier wakeups suspended or disabled for that loop.
- stateful generated harnesses expose initialization, validation, read-only query, record validation, and record application commands or document an accepted equivalent.
- participant-facing generated skills use harness commands for normal state mutation and query instead of raw SQL or ad hoc state-file edits.
- direct state edits are documented only as operator repair while paused, followed by harness validation.
- task-specific records, evidence models, scoring models, and domain tables appear only when introduced by intention source or generated clarification output.
- generated record contracts exist for structured bookkeeping that the harness or skills claim to apply.
- state contracts do not require a particular backend unless the generated loop explicitly selects it or the default sqlite rule applies because the SQL schema is clear.

Check workspace contracts:
- workspace setup contracts route workspace planning or creation through `prepare-workspace` and `houmao-utils-workspace-mgr` when the requested layout is a supported Houmao workspace flavor.
- default workspace policy is `in-repo` plus any explicitly listed loop bookkeeping directories, unless intention source chooses a different supported flavor or a custom operator-owned workspace.
- workspace contracts identify launch cwd, per-agent work roots, per-agent note or knowledge paths, writable temporary or artifact paths, shared resources, and read/write rules when those facts apply.
- managed workspace contracts identify workspace flavor, task name, repo or workspace root policy, expected or prepared concrete agent workspace names, launch profile names, launch cwd policy, loop bookkeeping directories, ignored transient paths, shared resources, and memo-seed posture when those facts apply.
- managed workspace contracts are shaped so `prepare-workspace` can consume prepared agent/profile facts from `prepare-agents` without inventing placeholder agent ids or launch profile names.
- workspace contracts or generated lifecycle docs identify the equivalent readiness facts required when an operator chooses manual workspace setup instead of the `prepare-workspace` command.
- custom operator-owned workspace contracts are explicit and do not pretend to be standard workspace-manager layouts.

Check execution stage boundaries:
- generated lifecycle docs or operator skills represent `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence when required, `validate-loop`, `launch-agents`, and `start` as separate ordered stages.
- `prepare-agents` guidance resolves concrete agent/profile and launch facts needed by workspace setup and live launch.
- `prepare-agents` guidance does not call, route to, plan, execute, create, repair, or otherwise perform `prepare-workspace`.
- `prepare-agents` guidance does not launch live agents as the normal preparation path.
- `prepare-workspace` guidance consumes prepared agent/profile facts and does not install generated skills, create specialists, launch agents, bind mail support, or perform `prepare-agents`.
- `validate-loop` guidance checks pre-launch readiness, including prepared agents, workspace readiness or equivalent manual evidence, mailbox/gateway/notifier posture, harness availability, run artifacts, launchability, and no in-chat waiting posture.
- `launch-agents` guidance launches prepared participants through maintained Houmao launch surfaces, reports live-agent/session facts, and does not send loop-start work.
- `start` guidance requires live-agent/session facts from `launch-agents` or an equivalent source, does not launch agents, and only sends the first loop trigger.
- missing live agent/profile/workspace/mailbox/gateway readiness is not an authoring-time package-shape failure; it is a `validate-loop` or `launch-agents` blocker.
- workspace postconditions distinguish ready facts, planned-but-not-executed facts, missing facts, and inconsistencies when the generated execplan records those reports.

Check run artifacts:
- durable-execution specs live under `execplan/specs/run/` when generated.
- durable-execution plans define a run artifact layout such as `runs/<run-id>/` or an explicit equivalent.
- the run artifact layout preserves structured payloads, rendered outputs, send or reply responses, records, state files, logs, evidence, and operator notes when the loop claims those artifacts exist.

Check final docs:
- final support docs use the canonical scaffold-owned named files under `execplan/docs/`, normally `artifact-index.md`, `operator-guide.md`, `runtime-model.md`, and `validation.md` when those views apply.
- `execplan/README.md` exists at the canonical scaffold-owned path when finalization emitted a package README.
- final support docs link or point back to authoritative `specs/`, `harness/`, `skills/`, and `agents/` artifacts rather than introducing standalone behavior.

Check execplan ADRs:
- execplan ADRs, when present, live under `execplan/adrs/` with sequential numeric filenames.
- execplan ADRs record accepted generated-artifact decisions, not user-editable intent decisions that belong under `intention/` or `<loop-dir>/adrs/`.
- affected artifacts named by execplan ADRs exist or are recorded as omitted or pending in the manifest, generated docs, or validation notes.

Check mail-driven communication contracts:
- mail-driven plans route mailbox setup, ordinary mail operations, gateway-notified rounds, managed-agent communication routing, and gateway lifecycle to maintained Houmao skills rather than generated platform mechanics.
- generated agent bindings for mail-driven participants include required maintained mail support skills for the participant's responsibilities.
- mail-driven plans document that Houmao notifier support is the runtime driver: a separate mail notifier detects open mail and prompts the target agent to process it.
- generated mail notification prompt guidance tells agents which mail/on-event skill to use and whether to run a follow-up on-tick skill after mail processing.
- generated bindings and operator-control material distinguish auto-mode notifier prompts from manual-mode operator prompts when manual operation is supported.
- generated control material routes notifier posture changes through maintained gateway support instead of generated harness or skill internals.
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
- generated on-tick skills are prompt-invoked bounded passes, not periodic background workers.
- manual-mode on-tick guidance performs one bounded pass and ends the turn; it does not wait for future mail or future status changes.
- generated role skills do not instruct agents to sleep, poll, tail logs, or wait in-chat for future mail or future ticks.

Check parseability and source posture:
- generated JSON schemas under `execplan/specs/comms/` or `execplan/specs/collab/records/` parse as JSON when present.
- generated TOML contracts parse as TOML when present.
- generated TOML files have plain human-readable comments above emitted section headers or table-array headers.
- generated TOML records or sections exposed through harness commands include concise `description` fields.
- private mechanical TOML files that are not exposed through harness commands do not require record-level `description` fields.
- generated harness commands or docs expose the loop's dynamic lookup and data-model mechanics when skills depend on harness lookup, schema validation, rendering, query, or controlled record application.
- harness output intended for agents uses a structured envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings, or documents an accepted equivalent.
- harness explanation surfaces expose structured rationale from generated contracts when generated skills rely on explanation behavior.
- harness commands that expose TOML-backed contracts use TOML `description` fields as the source for `--explain`, not parsed TOML comments.
- harness commands that expose JSON-schema-backed contracts use JSON Schema `description` fields where available.
- `--explain` output includes stable source keys or paths for explanation entries.
- when the harness command envelope requires JSON output for explanations, `--explain` is documented as requiring `--print-json` or an equivalent structured-output flag.
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
- whether the generated package shape appears ready for execution preparation subskills.

## Constraints

- Do not fix validation failures unless the user asked for repair or `update-execplan`.
- Do not fail only because `<loop-dir>/adrs/` is absent.
- Do not validate domain-specific fields unless the intention source introduced that domain.
