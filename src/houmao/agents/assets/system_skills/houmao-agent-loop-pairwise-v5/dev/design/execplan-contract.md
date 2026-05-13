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

Every emitted generated artifact directory should include a concise `README.md` with only `Purpose` and `Contents`. These README files orient readers; they do not duplicate contracts or become source authority.

The top-level skill currently requires only the broad layout. Future improvements should tighten validation by adding explicit checks for artifact coverage, parseability, schema/render pairing, agent binding fields, and harness command behavior.

## Default Scaffold Profile

The default scaffold is a flexible profile, not a rigid template. A useful generated loop normally has:

- a manifest-indexed generated package;
- machine contracts under `specs/`;
- generated role/event/tick skills under `skills/`;
- concrete agent bindings under `agents/`;
- a plan-local harness under `harness/`;
- generated support views under `docs/`;
- a workspace contract when agents need work roots or shared resources;
- a run artifact layout when execution produces durable payloads, records, logs, or evidence.

The generator may omit a default layer or file when the intention clearly does not need it. The omission should be explicit in the manifest, generated docs, or validation notes so later maintainers can distinguish a deliberate small loop from an incomplete plan.

Scaffold-owned starter files should be materialized centrally by `scripts/scaffold.py` from `assets/scaffolds/`. The relevant profiles are:

- `intention-create` for the basic editable intention source files: `intention/README.md` and `intention/loop-overview.md`;
- `intention-init` for initial loop setup: `intention/README.md`, `intention/loop-overview.md`, and `intention/project-context.md`;
- `execplan-shell` for the standard `execplan/` shell and manifest seed;
- `execplan-stepwise-shell` for the same shell plus `execplan/adrs/`;
- `execplan-finalize-docs` for scaffold-owned `execplan/README.md` and named docs starters;
- `execplan-adr` for one accepted execplan ADR file.

Runtime routed pages should reference `subskills/reference/scaffold-surface.md` and the relevant profile names instead of restating starter file bodies inline.

`init` owns project-context capture. It may use an explicit project root or project context supplied by the user, otherwise it performs lightweight nearby project detection and writes the result to `intention/project-context.md`. `create-intention` does not perform project scanning.

Expected generated paths should be explicit whenever a layer is used:

```text
execplan/
  README.md
  manifest.toml
  adrs/0001-short-decision-slug.md
  specs/
    README.md
    collab/collab-overview.md
    objective/objective.toml
    comms/templates.toml
    state/state-overview.md
    state/schema.sql
    state/seed.toml
    state/invariants.toml
    workspace/workspace.toml
    run/run-artifacts.toml
    participants/participants.toml
  skills/
    README.md
    <unique-skill-name>/SKILL.md
  agents/
    README.md
    bindings.toml
    profiles/<agent-id>/config.toml
    profiles/<agent-id>/definition.md
    notifier-prompts/<agent-id>.md
  harness/
    README.md
    commands.toml
    requirements.txt
    dependency-posture.toml
    vendor/
  docs/
    README.md
    artifact-index.md
    operator-guide.md
    runtime-model.md
    validation.md
```

Optional files may be omitted, but the process overview path, flat generated skill-directory shape, agent binding registry, and harness command registry should not be left implicit when those stages emit artifacts. `execplan/harness/dependency-posture.toml` is present when the generated harness imports non-stdlib Python libraries. `execplan/harness/requirements.txt` and `vendor/` are optional standalone/custom execution support, not the default dependency path. `execplan/adrs/` is optional and normally appears only for step-by-step generation decisions. Generated skill names must be unique after installation; do not rely on nested directories to disambiguate role, trigger, or purpose.

`clarify-execplan` may add `execplan/adrs/` after generation when the operator accepts implementation-level decisions about generated artifacts. Those ADRs should identify affected artifacts and any downstream stage that must be regenerated or marked stale. They must not become a place to invent missing user intent; intent gaps belong in `intention/` through `clarify-intent` or direct source edits.

## Staged Generation Order

The process model is the first generated authority. The default staged order is:

```text
execplan-specs-process
  -> execplan-specs-contract
      -> execplan-harness
          -> execplan-skills
              -> execplan-agent-bindings
                  -> execplan-finalize
```

`execplan-specs-process` emits the canonical process overview at `execplan/specs/collab/collab-overview.md`. It captures phases, events, handoffs, tick responsibilities, ownership, terminal posture, recovery posture, and provisional participant, message, state, or record families. It should also include a human-readable process explanation in two executable-looking views: Python-style pseudocode in fenced `python` blocks with inline comments for conditions/actions/state effects/stopping points, and a high-level Mermaid `sequenceDiagram` in a fenced `mermaid` block. Later stages derive concrete contracts and operational surfaces from that model. Do not use a flat `execplan/specs/process.md` as the primary process document.

`execplan-fast-forward` should first materialize `execplan-shell`, then run all stages in order without optional design questions. `execplan-step-by-step` should first materialize `execplan-stepwise-shell`, then run all stages with one-question-at-a-time generation decisions recorded under `execplan/adrs/`. `update-execplan` should choose the earliest affected stage and rerun downstream stages. `execplan-finalize` is last: it may populate scaffold-owned README/docs starters and finalize a manifest seeded earlier, but it should not add new authoritative behavior that bypasses process, contracts, harness, skills, or agent bindings.

## Participant And Agent Boundary

Generated plans should separate three identities:

- participant role templates or role descriptions;
- stable participant instances used by loop contracts and message routes;
- concrete Houmao agent bindings used for launch profiles, prompts, installed skills, workspace policy, and maintained support skills.

This separation lets one loop use a coordinator/worker pattern, another use peer reviewers, and another use a custom graph without changing the packaged skill. The topology is generated from intention source and clarification decisions, not from a built-in role set.

## Workspace Preparation Boundary

Workspace requirements belong in `execplan/specs/workspace/workspace.toml`. Concrete participant-to-agent/profile mapping belongs in `execplan/agents/bindings.toml`, which should reference the applicable workspace policy instead of replacing the workspace contract.

When managed workspaces are needed, the normal execution order is:

```text
prepare-workspace
prepare-agents
start
```

`prepare-workspace` adapts generated workspace contracts and agent bindings into `houmao-utils-workspace-mgr` inputs. It owns plan/execute routing, workspace-manager interaction, and readiness reporting for workspace docs, worktrees, knowledge paths, shared resources, bookkeeping paths, ignored transient paths, launch cwd posture, memo seeds, and mutable-path uniqueness.

`prepare-agents` owns profile and agent preparation only after workspace readiness exists. It may verify workspace facts as preconditions, but it should not call `prepare-workspace`, run the workspace manager, create worktrees, repair workspace directories, or route workspace setup.

## Runtime State Kernel

When a loop needs durable state, treat bookkeeping as runtime control-plane state. It answers scheduling, ownership, recovery, validation, transition-audit, and completion questions. It should not become another copy of mail or generated docs.

State should store compact facts and refs:

- plan metadata;
- process state;
- participants or role instances when they are not fully static elsewhere;
- work items, branches, claims, tasks, or open ends when the loop has goal-directed units;
- active ownership through handoffs or exchanges;
- communication payload lifecycle;
- attempts, decisions, evidence, and artifacts when the loop needs those facts;
- operator intent events;
- generic events.

State must not store full mail bodies, rendered Markdown, long rationale, pseudocode, detailed analysis, or documentation content. Mail remains the communication authority. Artifacts and docs remain the authority for rich evidence and explanation. State stores message IDs, payload IDs, artifact paths, commit refs, scalar gates, decisions, statuses, timestamps, and other compact facts.

Default backend selection:

- use sqlite when stable entities and transitions can be expressed as a clear SQL schema;
- include `specs/state/schema.sql` as the field-level authority for sqlite;
- include `specs/state/state-overview.md`, `seed.toml` when deterministic initialization is needed, and `invariants.toml` when validation needs named checks;
- use JSONL plus explicit schemas only for append-only, schema-light, or intentionally denormalized state;
- avoid unstructured ad hoc state files when sqlite or JSONL plus schema is feasible.

Task-specific records, scoring, evidence models, and domain tables are extensions. They should be generated only when the intention introduces them. The default rule is that communication carries rich human meaning, state carries compact auditable facts, the harness validates/applies narrow records, and role skills decide which records should exist.

## TOML Readability And Explanation

Generated TOML contracts should be readable directly and explainable through the harness:

- put a plain human-readable comment above every generated section or table-array header;
- include concise `description` fields for records, sections, or non-obvious fields exposed through harness commands;
- use `description` fields as the source for harness `--explain`;
- do not parse comments for harness explanations;
- do not require descriptions for private mechanical TOML files that are never exposed to agents or operators.

Example:

```toml
# Runtime state backend used by the generated harness.
[state_backend]
kind = "sqlite"
description = "Run-scoped sqlite database used as the live bookkeeping authority."
schema_path = "specs/state/schema.sql"
```

## Harness Boundary

The harness is a plan-local data-model and dynamic-lookup surface. It can validate contracts, render views, explain generated TOML fields, query state, check completion, and apply schema-validated records.

Harness command registries and config should reference generated package artifacts by relative path. The harness can read `../specs/...`, `../agents/...`, and other files in the same generated loop-definition package. If harness scripts need stable local paths, generate relative symlinks under `harness/refs/` that point to the authoritative package artifacts. If symlinks cannot be created because of filesystem permissions or environment limits, scripts should use direct relative paths instead. `harness/schemas/` is for harness-owned schemas such as command envelopes; generated communication, record, state, workspace, participant, and objective schemas stay authoritative under `specs/` and should not be copied into `harness/`.

Harness implementations may use `click` for command routing, `jinja2` for `.md.j2` Markdown rendering, and `jsonschema` for schema validation. These are normal Houmao runtime dependencies. The intended dependency policy is Houmao-installed-environment first, caller-selected environment second, and optional local-pip-target only for standalone/custom execution:

- first prove imports through the intended harness interpreter and record `houmao-env`, `environment-provided`, or an equivalent posture when they work;
- when imports fail, generated entrypoints report the missing dependency and guide the caller to install it into the active harness Python environment or run with the Python environment associated with the installed Houmao uv tool;
- generated guidance should point to uv inspection or refresh commands such as `uv tool list --show-paths --show-python` without hardcoding uv internals;
- when a generated harness test fails because dependencies are missing or the wrong interpreter appears active, retry the same test through the Houmao uv-installed environment before treating it as a harness implementation bug;
- only when standalone/custom execution is intentionally supported, generate `execplan/harness/requirements.txt`, optional `vendor/`, the local target install command `python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt`, and a `vendor/` import bootstrap.

Local dependency files are harness implementation support. They do not move schema, renderer, policy, state, workspace, participant, or objective authority out of `specs/`.

The harness should not own Houmao platform operations. Mailbox delivery, mailbox administration, gateway posture, managed-agent launch, prompt transport, memory updates, inspection, and workspace creation remain delegated to maintained Houmao skills or supported CLI surfaces.

Harness output intended for agents should use a stable machine-readable envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings. Explanation commands should derive agent-readable rationale from TOML `description` fields and JSON Schema `description` fields, with stable source keys. If the command envelope requires JSON output for explanations, require `--print-json` with `--explain`.

For stateful loops, the harness should expose:

- `state init`;
- `state validate`;
- `state query`;
- `record validate`;
- `record apply`;
- optional `state export` for compact human recovery views.

Participant agents should use those commands for normal state access. Raw SQL or direct state-file edits are operator repair actions only, performed while paused and followed by harness validation.

## Communication Default Contract

Ordinary cross-agent participant handoffs default to Houmao mail unless the intention source explicitly selects a non-mail mechanism. The generator should not preserve a design gap that asks "should participants use mail?" when the source is silent; the useful questions are loop-specific: which roles communicate, which message families exist, which payload fields are required, which replies are expected, and which state or records change.

Mail-driven execplans should keep semantic ownership in generated material and mechanical ownership in maintained Houmao skills. Generated specs define routes, message families, schemas, renderers, reply links, lifecycle records, and event/tick behavior. Maintained skills own mailbox setup, ordinary mail operations, gateway-notified mail rounds, managed-agent communication routing, and gateway posture.

Houmao mail-driven loops are notifier-prompt-driven. The Houmao email/notifier system runs outside the target agent, detects open mail, and sends the target agent a prompt. That prompt is the normal wakeup mechanism for mail-received event skills, and it may include loop-specific instructions such as "after processing this mail, call the coordinator tick skill." Agents should finish the chat turn after processing mail and any requested tick. They should not sleep, poll, tail logs, or wait in-chat for future work, because holding the chat turn open blocks later mail notification prompts from being handled.

On-tick skills are prompt-invoked bounded passes, not periodic background workers. There is no separate periodic tick driver that wakes agents independently. If a loop needs a tick after mail processing, record that in generated notifier prompt guidance or equivalent agent binding material.

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

## Event And Tick Skill Boundary

Generated skills should be scoped by role and trigger. On-event skills handle concrete events such as a received schema-specific mail family. On-tick skills handle scheduling, reconciliation, timeout, completion, and "what happens next" work that is not owned by one incoming event.

Tick skills should inspect dynamic state through specs or harness commands, perform the first applicable bounded action or report no action, and stop. They should not become a hidden global runner.

## Run Artifact Boundary

When execution produces durable artifacts, the generated plan should preserve them under a run layout such as `<loop-dir>/runs/<run-id>/` or an explicit equivalent. Useful durable artifacts include structured payloads, rendered messages, send or reply responses, record files, state files, logs, evidence, and operator notes.

Status and recovery should be able to refer to the run artifact layout without depending only on live mailbox state.

## Source Boundary

`intention/` is the editable source of truth. `execplan/` is generated output updated from that source.

When generated material needs richer policy than the current intention states, the generator should preserve an explicit unresolved entry instead of copying assumptions from a domain-specific example.

## Reference Shape

A mature generated loop plan is useful as a reference for the depth of a complete execplan, not as a global template. Useful reference traits include:

- structured TOML contracts under `specs/`;
- schema-validated communication and record payloads with Markdown renderers when human-readable output is needed;
- compact state contracts when runtime state is needed;
- participant role templates separated from concrete agent bindings;
- generated skills scoped to role events, plus prompt-invoked tick skills for scheduler-like responsibilities;
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
- check generated TOML section comments and `description` fields for harness-explainable records;
- validate skill frontmatter for every generated skill;
- validate generated artifact directory README files exist and use only `Purpose` and `Contents`;
- validate state contract coherence, including state overview, sqlite schema or JSONL schemas, invariants, and harness command coverage;
- validate generated communication and record registries connect schema ids, payload formats, and renderers coherently;
- validate agent configs include participant identity, prompt source, installed skills, and workspace policy;
- validate supported workspace setup routes through `houmao-utils-workspace-mgr` rather than generated ad hoc worktree mechanics;
- validate harness dependency posture, feature-scoped declarations, import-failure guidance, optional local requirements, install diagnostics, stale wheelhouse claims, and import bootstrap when generated harness code imports non-stdlib libraries;
- run harness self-checks when present;
- report stale or ambiguous generated-source metadata;
- keep domain-specific validation opt-in and derived from the loop source.
