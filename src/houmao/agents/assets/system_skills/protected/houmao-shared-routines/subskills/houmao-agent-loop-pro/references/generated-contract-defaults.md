---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Generated Contract Defaults

## Purpose

Use this page when generating, validating, finalizing, or operating against generated `execplan/` contracts.

Use these defaults unless intention source or accepted clarification decisions choose an equivalent or narrower shape. Any equivalent or omission must be indexed or explained in `manifest.toml`, generated docs, or validation notes.

## Execplan Scaffold

- `manifest.toml` indexes generated artifacts, generated-source posture, and plan revision.
- Every emitted generated artifact directory has a concise `README.md` with only:
  - `Purpose`: why the directory exists;
  - `Contents`: files or child directories in that directory.
- `adrs/` records accepted execplan-generation decisions when `execplan-step-by-step` is used.
- `specs/collab/collab-overview.md` is the required process-first authority.
- `specs/` separates objective, collaboration, communication, state, workspace, run-artifact, and participant contracts when those concerns apply.
- `skills/` contains one flat directory of generated skills: `skills/<unique-skill-name>/SKILL.md`.
- Generated skill names must be unique after installation; encode purpose in the skill name or metadata, not in nested category directories.
- `agents/` binds concrete Houmao agents to participant instances, prompt sources, installed skills, notifier prompt text, and workspace policy.
- `harness/` exposes loop-local validation, dynamic lookup, rendering, query, and controlled record application through an explicit command registry.
- `docs/` explains generated contracts for humans but is not source authority; final docs live under named files, not loose unindexed notes.

## Participants

- Separate participant role templates, stable participant instances, and concrete agent bindings.
- Do not force a fixed participant topology or role count.
- Generate task-specific records only from intention source or clarification decisions.

## Topology And Routing Defaults

- Generated execplans record one topology mode when participant routes are non-trivial:
  - `tree-loop`: local-close tree or forest execution; normal results reply to immediate upstream.
  - `generic-loop`: directed routes may be non-tree or cyclic when context, dedupe, termination, and result routing are explicit.
- Store machine-readable topology contracts under `specs/collab/topology/` when validation or harness lookup needs them.
- `tree-loop` direct participant cycles are invalid unless an accepted normalization chooses an existing participant as relay, root, aggregator, or cycle breaker and records the resulting tree or forest.
- `generic-loop` cycles define termination, dedupe or repeat-visit posture, active ownership, and result routing before runtime artifacts are generated.
- Do not require a master, lead, coordinator, or root owner unless intention source or accepted clarification decisions choose one.

## Predecessor Context Defaults

- Generic-loop routes consider predecessor-context needs route by route or message family by message family.
- Carry selected upstream refs, summaries, artifacts, branch or commit refs, state refs, evidence refs, or current-hop deltas only when the generated process says the receiver needs them.
- If no predecessor context is needed, record explicit omission when the route is non-obvious.
- Do not force a fixed context bundle across every generic route.
- State stores compact lineage and refs; rendered mail or artifacts store readable context.

## Mail Schema Event Defaults

- Templated participant mail uses `schema_id` as the loop-local mail type.
- `specs/comms/templates.toml` maps template names to `schema_id`, schema path, renderer path, payload format, and reply expectation when applicable.
- Outgoing mail follows `TOML payload -> JSON Schema validation -> Markdown rendering -> Houmao mail delivery`.
- Rendered mail includes a parseable in-body `houmao-email-metadata` fenced block near the top.
- Generated on-event mail skills state their exact triggering `schema_id`.
- Unknown, malformed, operator-origin, or freeform mail uses explicit generated fallback paths only when needed.

## Bookkeeping State

Treat bookkeeping as runtime control-plane state, not working memory.

State stores compact facts:
- ids and refs;
- statuses and ownership;
- decisions and scalar gates;
- evidence links;
- transition audit;
- completion posture.

Mail, docs, and artifacts store rich material:
- prose;
- rationale;
- rendered Markdown;
- pseudocode;
- analysis;
- detailed evidence.

Important transitions must be reconstructable from:
- changed entity;
- source actor or event;
- new state or decision;
- mail, evidence, or artifact refs;
- timestamp.

Active ownership must be queryable enough for scheduling and recovery.

## Operator Control Defaults

When a generated loop has lifecycle or mode control needs:

- generate one loop-local operator skill named `<loop-slug>-operator-control`;
- put it directly under `execplan/skills/`;
- make it identify the loop slug, loop dir, manifest, harness, agent bindings, and supported lifecycle operations;
- keep platform mechanics routed to maintained Houmao skills.

Keep run lifecycle state separate from execution mode:

- `run_state`: values such as `not_started`, `running`, `paused`, `recovering`, `stopped`, and `completed`;
- `execution_mode`: `auto` or `manual` when both modes apply.

Mode meanings:

- `auto`: the default mode; notifier prompts are the normal wakeup path for mail-driven participants.
- `manual`: notifier wakeups are suspended or disabled for the loop, and the operator prompts bounded participant turns.

Rules:

- Default initial `execution_mode` to `auto` unless intention source, accepted clarification decisions, or operator-control state explicitly selects another mode.
- `manual` is not `paused`; pause blocks normal progress, while manual changes wakeup authority.
- Record mode switches, pause, resume, stop, override, and recovery as operator intent events when those controls exist.
- Generated harnesses expose mode and control context; generated skills do not infer mode from intention Markdown or static prose.

## State Contracts

When durable bookkeeping is needed, generate state contracts under `execplan/specs/state/`:

- `state-overview.md` for authority, boundaries, entity families, transitions, invariants, scheduling queries, and non-state content;
- `schema.sql` when sqlite is selected;
- `seed.toml` when deterministic initialization is needed;
- `invariants.toml` when validation needs named checks;
- JSON schemas for JSONL records when JSONL is selected.

Default state backend order:
- use sqlite when stable entities and transitions can be expressed as a clear SQL schema;
- use JSONL plus explicit schemas only for append-only, schema-light, or intentionally denormalized state;
- avoid unstructured ad hoc state files when sqlite or JSONL plus schema is feasible.

Consider generic families such as:
- plan metadata;
- process state;
- control state;
- participants;
- work items;
- handoffs or exchanges;
- communication payload lifecycle;
- attempts;
- decisions;
- evidence;
- artifacts;
- operator intent events;
- generic events.
- generic-loop lineage and visited node or edge facts when cycles or repeat visits exist;
- cycle iteration counts and active ownership when generic loops need them.

## Generated TOML

- New generated topology TOML uses `tree-loop` or `generic-loop` as the mode value.
- Validation accepts legacy mode aliases recorded by older artifacts: `pairwise-tree`, `pairwise-loop`, `pairwise`, `generic-graph`, and `generic graph`.
- Generated TOML sections have plain human-readable comments above each section or table-array header.
- Agent-facing or harness-facing TOML records include concise `description` fields.
- `description` fields, not comments, are the source for harness `--explain`.
- Private mechanical TOML files that are never exposed through harness commands do not need record-level descriptions.

## Skill And Harness Defaults

- Generated on-event skills handle one concrete incoming event or message family, perform one bounded role-owned action, then stop.
- Generated on-tick skills handle scheduling, reconciliation, timeout, completion, or "what now" decisions by querying harness control context when available, doing at most one pass, then stopping.
- In `auto` mode, on-tick skills perform notifier-prompted follow-up work.
- In `manual` mode, on-tick skills perform one operator-prompted pass: check relevant mail or state, act on one bounded item, send or reply when required, record through the harness, then stop.
- Generated skills query specs, state, or harness output for dynamic policy and runtime facts instead of copying constants into static prose.
- Generated harnesses may use `click` for modular commands, `jinja2` for `.md.j2` rendering, and `jsonschema` for validation when needed.
- Generated import failures should guide callers to install missing libraries into the active harness Python environment or use the Houmao uv-installed environment.
- Stateful generated harnesses expose normal participant access through commands for state initialization, validation, read-only query, record validation, and record application.
- Controllable generated harnesses expose read-only `control status` and `control get-mode` commands, controlled mode or lifecycle commands when supported, and participant-specific manual context when manual mode is supported.
- Generated harness commands that expose TOML-backed contracts support `--explain` when structured descriptions exist, with stable source keys in machine-readable output.

## Workspace And Runs

- Generated workspace contracts identify launch cwd, agent work roots, standard workspace-manager surfaces, shared resources, validation command inputs, and read/write rules when applicable.
- Managed workspace contracts include workspace-manager inputs when applicable: operation intent (`plan`, `create`, `validate`, or `summarize`), workspace flavor, task name, repo or workspace root policy, concrete agent workspace names, project profile or explicit raw launch profile names, launch cwd policy, `shared-kb/`, `owner-states/<subdir>/...`, per-agent `states/`, shared resources, validation commands, and memo-seed posture.
- Generated agent bindings reference workspace policies from `specs/workspace/`; they do not replace the workspace contract.
- Generated execution preserves durable payloads, rendered outputs, send or reply responses, records, state files, logs, and evidence under a run artifact layout such as `<loop-dir>/runs/<run-id>/`.
- Omit unused default layers only when the manifest and generated docs make the omission explicit.

## Execution Stage Defaults

- `prepare-agents` materializes launchable Houmao project profiles, generated skill bindings, definitions, notifier prompt paths, memo posture, pending cwd posture, and prepared agent facts.
- `prepare-agents` does not launch live agents as normal preparation behavior.
- `prepare-workspace` adapts generated workspace contracts, agent bindings, and prepared agent/profile facts into `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr` `plan`, `create`, `validate`, or `summarize` inputs.
- Workspace readiness may also come from explicit manual evidence when the generated execplan records the required facts.
- `validate-loop` checks concrete pre-launch readiness, including mailbox, gateway, memory, notifier, harness, state, run-artifact, and launchability posture before `launch-agents`; `validate-execplan` only checks generated package shape and contracts.
- `launch-agents` launches prepared participants through maintained Houmao launch surfaces and reports live-agent/session facts without beginning loop work.
- `start` begins loop work by sending the first trigger after required agents are live; it does not launch agents.
- `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence, `validate-loop`, `launch-agents`, and `start` are separate ordered stages.
- `prepare-workspace` and `prepare-agents` do not call each other.
- Missing profile, workspace, mailbox, gateway, harness, state, run-artifact, launchability, or live-agent readiness is a `validate-loop` or `launch-agents` blocker, not a `validate-execplan` failure.
