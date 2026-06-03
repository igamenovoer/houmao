# Reference Execplan Patterns

This note records generic patterns extracted from a mature generated `execplan/` package. It is developer reference material only. It is not part of skill execution and does not make any specific domain, topology, toolchain, scheduling policy, or evidence rule global behavior.

## Package Shape

A mature `execplan/` package usually needs more than the minimum directory shell:

```text
execplan/                         # Generated operational package; replaceable from intention source.
  README.md                       # Purpose-and-contents orientation for the generated package.
  manifest.toml                   # Package index: artifact ids, paths, purposes, generated-source posture, and plan revision.
  adrs/                           # Optional execplan-generation decision records for step-by-step generation.
  specs/                          # Machine-readable contracts. Agents should consult these through skills or harness commands.
    README.md                     # Purpose-and-contents orientation for generated specs.
    objective/                    # Goals, constraints, success posture, and references to policy sections.
    collab/                       # Process topology, scheduling policy, handoff rules, and structured collaboration record schemas.
      collab-overview.md          # Required canonical process overview for generated plans.
    comms/                        # Mail/message schemas, payload-to-renderer registry, and human-readable render templates.
    state/                        # Runtime state model: schema, migrations, seed data, and invariants when the loop needs state.
    workspace/                    # Workdir, command, artifact, environment, path contracts, and workspace-manager inputs.
    run/                          # Run artifact layout and recovery/audit preservation contracts.
    participants/                 # Abstract roles and stable role instances; not concrete Houmao agent processes.
  skills/                         # Flat generated skill directories; each name must be unique after installation.
    README.md                     # Purpose-and-contents orientation for generated skills.
  agents/                         # Concrete Houmao agent bindings, profile material, and notifier prompt text.
    README.md                     # Purpose-and-contents orientation for generated agent bindings.
  harness/                        # Plan-local command registry and implementation surface for validation, query, rendering, dynamic lookup, and controlled apply.
    README.md                     # Purpose-and-contents orientation for generated harness artifacts.
    requirements.txt              # Optional local dependency declaration when the harness needs non-stdlib libraries.
    dependency-posture.toml       # Optional dependency posture, interpreter evidence, import guidance, and diagnostics record.
    vendor/                       # Optional standalone harness-local pip target; implementation support, not contract authority.
  docs/                           # Named generated human support views. Helpful for readers, but not the operational source of truth.
    README.md                     # Purpose-and-contents orientation for generated support docs.
```

The shape matters because each layer has a different authority:

| Layer | Pattern |
| --- | --- |
| `manifest.toml` | Generated artifact index and plan revision anchor. |
| `adrs/` | Optional accepted decisions about generated artifact shape, used by step-by-step generation. |
| `specs/` | Machine contracts that role skills and harness commands consult. |
| `skills/` | Flat generated skill directories with `SKILL.md`; trigger or responsibility is encoded in the unique skill name and metadata. |
| `agents/` | Concrete Houmao agent bindings for participant instances, profile material, installed skills, workspace policy, and notifier prompt text. |
| `harness/` | Deterministic local command registry and implementation surface for validation, query, rendering, policy, and controlled record application. |
| `docs/` | Named generated human views that explain the package but defer authority to `specs/`. |

The packaged skill should materialize the starter shell for these paths through shared scaffold profiles and template assets, not through repeated page-local prose. The reusable scaffold ownership surface is:

```text
houmao-agent-loop-pro/
  scripts/
    scaffold.py                  # Shared scaffold generator.
  assets/
    scaffolds/
      intention/                 # Starter intention Markdown.
      execplan/                  # Manifest seed, package README/docs starters, and ADR template.
```

Every emitted generated artifact directory should have a local `README.md` with only `Purpose` and `Contents`. A simple generated skill directory can omit its own README when it contains only `SKILL.md` and optional `agents/openai.yaml`, because `SKILL.md` orients that skill; `execplan/skills/README.md` still orients the collection.

### Abstract Example Shape

The following example is abstracted from a concrete planner/reviewer/worker reference plan. It shows the kind of file-level detail a mature execplan may contain without making that exact topology or domain mandatory.

```text
execplan/
  manifest.toml
  README.md
  adrs/
    0001-message-family-shape.md
  specs/
    objective/
      README.md
      objective.toml              # Goal and constraints rendered by the harness.
      policy.toml                 # Objective-level policy and evidence gates.
    collab/
      README.md
      collab-overview.md          # Canonical process overview: phases/events/handoffs/ticks plus Python pseudocode and Mermaid sequence graph.
      loop-policy.toml            # Scheduling order, ownership rules, terminal conditions, and derived values.
      topology/
        topology.toml             # Allowed participant-to-participant message routes.
        graph.md                  # Human-readable topology view.
      records/
        handoff.schema.json       # Structured record for work ownership and message refs.
        attempt.schema.json       # Structured record for one work attempt.
        evidence.schema.json      # Structured record for evidence produced during work.
        decision.schema.json      # Structured record for review or routing decisions.
        operator-intent.schema.json
        README.md
    comms/
      README.md
      templates.toml              # Registry mapping schema ids to renderers.
      schemas/
        README.md
        implementation-request.schema.json
        implementation-reply.schema.json
        review-request.schema.json
        review-reply.schema.json
        freeform-notice.schema.json
        ack.schema.json
      renderers/
        README.md
        implementation-request.md.j2
        implementation-reply.md.j2
        review-request.md.j2
        review-reply.md.j2
        freeform-notice.md.j2
        ack.md.j2
    state/
      README.md
      state-overview.md           # State authority, boundaries, entity families, transitions, invariants, and non-state content.
      schema.sql                  # Runtime tables for compact bookkeeping; enough for the current generated revision.
      seed.toml                   # Initial state facts or bootstrap values when needed.
      invariants.toml             # Runtime consistency rules checked by the harness.
    workspace/
      README.md
      workspace.toml              # Workdir, command, artifact, runtime path, and workspace-manager contracts.
    run/
      README.md
      run-artifacts.toml          # Run directory layout, artifact preservation, audit, and recovery posture.
    participants/
      README.md
      participants.toml           # Role templates and stable role instances.
      planner.md
      reviewer.md
      worker.md
  skills/
    team-example-shared-harness-usage/
      SKILL.md                    # Role-neutral mechanics for invoking the harness.
      references/
        command-shape.md
        email.md
        records.md
        state-query.md
    team-example-planner-on-loop-start/
      SKILL.md                    # On-start handler: initialize or verify run posture, objective, base state, and first route.
    team-example-planner-on-schedule-tick/
      SKILL.md                    # On-tick handler: inspect current state and perform one bounded scheduling or completion action.
    team-example-planner-on-implementation-reply-received/
      SKILL.md                    # On-mail handler: process a worker result reply, validate records, and decide the next handoff.
    team-example-worker-on-implementation-request/
      SKILL.md                    # On-mail handler: accept assigned work, perform it, and return a schema-validated result or notice.
    team-example-reviewer-on-review-request/
      SKILL.md                    # On-mail handler: review submitted evidence or direction, then return a structured decision.
    team-example-operator-control/
      SKILL.md                    # Loop-local operator control: identity, lifecycle, mode switching, manual steps, and recovery routing.
      README.md
      subskills/
        status.md
        prepare-agents.md
        prepare-workspace.md
        validate-loop.md
        launch-agents.md
        start.md
        set-mode.md
        pause.md
        resume.md
        stop.md
        recover.md
        manual-step.md
  agents/
    README.md
    bindings.toml                 # Participant-to-agent map, installed generated skills, system-skill preinstall posture, prompt source, and workspace policy.
    profiles/
      planner/
        config.toml               # Concrete agent binding for participant `planner`.
        definition.md             # Prompt source for the concrete agent.
      reviewer/
        config.toml
        definition.md
      worker-1/
        config.toml
        definition.md
      worker-2/
        config.toml
        definition.md
    notifier-prompts/
      planner.md                  # Loop-specific mail notification prompt appendix when needed.
      reviewer.md
      worker-1.md
      worker-2.md
  harness/
    README.md
    commands.toml                 # Harness command registry.
    requirements.txt              # Only present when local non-stdlib harness dependencies are needed.
    dependency-posture.toml       # Records Houmao-env/environment/local posture, interpreter evidence, import guidance, commands, and diagnostics.
    schemas/
      command-envelope.schema.json
    refs/
      comms-templates.toml        # Relative symlink to ../../specs/comms/templates.toml when local script paths help.
      state-schema.sql            # Relative symlink to ../../specs/state/schema.sql when present.
    bin/
      loopctl                     # Executable shim.
    src/
      cli.py                      # Command registration.
      common.py                   # Shared data-model, output, and lookup helpers.
      commands/
        validation.py
        query.py
        policy.py
        objective.py
        email.py
        records.py
    vendor/                       # Optional pip --target directory for standalone/custom execution.
  docs/
    README.md
    artifact-index.md
    operator-guide.md
    runtime-model.md              # Human explanation of runtime flow.
    validation.md
```

In this example, `implementation-request` mail is produced from a TOML payload, validated against `specs/comms/schemas/implementation-request.schema.json`, rendered through `specs/comms/renderers/implementation-request.md.j2`, and sent through maintained Houmao communication surfaces. The receiver's `worker-on-implementation-request` skill handles that event, uses `shared-harness-usage` for mechanics, and records compact bookkeeping through harness record commands when appropriate.

The planner's tick skill is separate from mail-received handlers. It asks the harness for current control context, state, policy, ownership, and completion posture, then performs one bounded scheduling action or reports no action. This keeps dynamic values in `specs/`, runtime state, and harness output instead of freezing them inside static skill text.

The operator-control skill is loop-bound, so it carries the concrete loop slug and generated package paths instead of asking the operator to restate loop identity for every lifecycle action. It routes platform mechanics to maintained Houmao skills while using generated harness control commands for run state, execution mode, and operator intent records.

Workspace setup in this abstract example is not implemented by generated role skills or agent preparation. The generated workspace contract should provide policy and structured inputs for `prepare-workspace`, which routes supported layouts through `houmao-utils-workspace-mgr` `plan`, `create`, `validate`, and `summarize`; the default is the standard `in-repo` flavor with task `shared-kb/` for cross-run knowledge, task `owner-states/<subdir>/...` for per-run task-owner bookkeeping, per-agent `repo/` worktrees for source mutation, per-agent `states/` for agent-local bookkeeping, and validation commands when project-scope readiness checks are known.

`prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence, `validate-loop`, `launch-agents`, and `start` are separate ordered execution stages. `prepare-agents` resolves concrete agent/profile and launch facts first. `prepare-workspace` consumes those facts with generated workspace contracts to prepare or verify workspace facts. `validate-loop` checks concrete pre-launch readiness, including workspace, mailbox/gateway/notifier, harness, run artifact, state, launchability, and no in-chat waiting posture. `launch-agents` starts prepared agents and reports live-agent/session facts. `start` sends the first loop trigger after agents are live. After launch, `<loop-slug>-operator-control` is the loop-local lifecycle surface for status, start, pause, resume, stop, recover, mode switching, and manual stepping when those operations apply.

## Core Runtime Patterns

The three central execplan patterns are:

```text
agent work loop
  ├── harness owns data-model mechanics and dynamic lookup
  ├── mail drives cross-agent process flow through schema-validated rendered messages
  └── skills implement event and tick behavior around that mail/state loop
```

The harness should keep data and dynamic runtime knowledge out of static skills. Mail should be the normal process driver between participants. Generated skills should be thin role-specific handlers around events, ticks, harness calls, and maintained Houmao platform surfaces.

## Default Scaffold Profile

The reusable default is a scaffold profile, not a mandatory full template. Start from:

- manifest-indexed generated package;
- purpose-based specs;
- role/event/tick skills;
- concrete agent bindings;
- plan-local harness;
- generated support docs;
- workspace contract when agents need work roots or shared resources;
- run artifact layout when execution produces durable payloads, records, state, logs, or evidence.

Small loops may omit unused default files. The omission should be explicit in the manifest, docs, or validation notes so a later agent can tell the difference between a deliberate small plan and an incomplete plan.

Starter files that belong to this reusable shell should come from the packaged scaffold profiles:

- `intention-create`
- `intention-init`
- `execplan-shell`
- `execplan-stepwise-shell`
- `execplan-finalize-docs`
- `execplan-adr`

Derived process, contract, harness, skill, and binding semantics should still be generated by the staged authoring pages rather than frozen into the scaffold layer.

Use `intention-create` for only the editable intention README and overview. Use `intention-init` for full loop initialization, including `intention/project-context.md`; project context may come from an explicit user-supplied project root, user-supplied context text, or lightweight nearby project detection. Project scanning is not part of `create-intention`.

## Staged Generation Pattern

The dependency-safe generation order is process-first:

```text
execplan-specs-process
  -> execplan-specs-contract
      -> execplan-harness
          -> execplan-skills
              -> execplan-agent-bindings
                  -> execplan-finalize
```

The process stage emits `specs/collab/collab-overview.md` as the canonical process overview. That file captures how the loop moves work: phases, events, handoffs, tick responsibilities, ownership, terminal posture, recovery posture, and provisional participant, message, state, or record families. It should also include a readable Python-style pseudocode view and a high-level Mermaid sequence graph. The pseudocode should live in fenced `python` blocks, use generic role/event/state names from the generated loop, and include inline `#` comments explaining conditions, actions, state effects, and stopping points. The sequence graph should live in a fenced `mermaid` block and show the participant/event/handoff flow at a level that downstream contract, harness, skill, and agent-binding stages can derive from. This stage is the first generated authority because downstream artifacts should not invent independent process semantics. Do not use a flat `specs/process.md` for the primary process overview.

The contract stage turns the process model into objective, participants, topology, communication, state, records, workspace, and run contracts. The harness reads those contracts. Skills read process/contracts/harness. Agent bindings install the generated skills. Final docs and manifest summarize what already exists.

## Manifest Pattern

`manifest.toml` is the package discovery surface. It should carry:

- stable `artifact_id`;
- `generated_source = true`;
- one `plan_revision` shared by generated artifacts;
- top-level `purpose_directories`;
- repeated `[[artifacts]]` entries with `artifact_kind`, `id`, `path`, and `purpose`.

A future stricter validator should parse the manifest and check that every indexed file exists, every generated file has a coherent purpose, and every artifact kind is known or intentionally extension-owned.

## Specs Pattern

A mature execplan can use purpose-based specs instead of one monolithic contract:

- `specs/objective/`: goals, constraints, and objective policy references.
- `specs/collab/`: scheduling policy, topology, collaboration records, and loop behavior.
- `specs/comms/`: message template registry, JSON schemas, and Markdown renderers.
- `specs/state/`: state schema, migrations, seed data, and invariants when runtime state is needed.
- `specs/workspace/`: repository, command, workspace, standard workspace-manager surfaces, validation command contracts, and inputs for `houmao-utils-workspace-mgr`.
- `specs/run/`: run directory layout, durable artifact preservation, audit, status, and recovery posture.
- `specs/participants/`: abstract role templates and stable role instances.

The general lesson is that runtime agents should consult structured contracts for policy and gates. They should not preserve important policy only in prose role instructions.

## Participant And Agent Binding Pattern

Execplans should separate participant identity from concrete Houmao agents:

- participant role templates describe abstract responsibilities;
- participant instances provide stable loop identities;
- `agents/bindings.toml` maps participant instances to concrete Houmao agent ids, generated skills, Houmao system-skill preinstall posture, prompt source, workspace policy, and notifier prompt path;
- `agents/profiles/<agent-id>/config.toml` binds one concrete Houmao agent to one participant instance;
- generated `definition.md` files provide prompt source material for those concrete agents.

Concrete agent configs should include participant identity, role spec, definition source, installed skills, skill installation mode, memo seed policy, workspace policy, and launch policy. Future agent-binding validation should check for those concepts even when individual loops name or extend them differently. When the workspace policy is a supported Houmao layout, the binding should point to the generated workspace contract and expose the concrete identity fields that `prepare-agents` confirms for `prepare-workspace` and `launch-agents`, not to ad hoc generated worktree setup steps.

## Skill Pattern

Generated skills should be event-scoped, tick-scoped, and role-scoped. The pattern is not any exact event set. The reusable pattern is:

1. Use one concise skill per meaningful event or lifecycle action.
2. Keep mechanical harness usage in a shared helper skill.
3. Keep role-specific decision authority in the active role/event skill.
4. Route domain mechanics to domain skills only when the loop intention and generated agent bindings install them.
5. Avoid letting one generated skill perform unrelated roles.

### Event Skills

On-event skills implement behavior caused by a concrete process event. In mail-driven loops, the common event is "participant received message with schema id X"; other loops may use other explicit event sources. The skill should:

- define the trigger precisely;
- state which participant or role owns the response;
- read or query only the context needed for that event;
- validate or render outgoing payloads through the harness when structured output is required;
- create or apply only the records the role owns;
- stop after the bounded event response instead of recursively driving the whole loop.

### Tick Skills

Some responsibilities do not conceptually belong to one incoming event. A loop may need on-tick skills for scheduling, reconciliation, completion checks, timeout handling, prompted status checks, or "what happens next" decisions. Tick skills should still be bounded: inspect current control context and dynamic state through the harness, perform the first applicable action or report no action, then stop.

Tick skills are useful when the loop has a role that coordinates process flow. They should not become a catch-all for all role behavior; event-specific work should stay in event skills.

In Houmao mail-driven loops, tick skills are not periodic background workers. The Houmao email/notifier process runs separately, detects mail, and prompts the target agent. A loop-specific notification prompt may tell the agent to call a tick skill after processing mail. The agent then ends the chat turn and waits for the next notifier or operator prompt. Generated skills should never keep a chat turn open by sleeping, polling, tailing logs, or waiting for future mail, because that prevents later notifier prompts from being handled.

For controllable loops, tick skills should branch on harness execution mode. In default `auto`, the notifier prompt remains the wakeup path. In `manual`, notifier wakeups are suspended or disabled and the operator prompts one bounded participant pass; the tick may inspect current mail or state, apply records, send downstream mail, reply upstream mail, or report no action, then stop. `manual` is not `paused`: pause blocks progress, while manual changes wakeup authority.

## Communication Pattern

Generated loop process is normally driven by mail communication between participants. This is a default, not a global restriction: an intention source may explicitly choose a non-mail mechanism, but ordinary participant handoffs should not require a fresh foundational transport decision.

Generated mail should be structured as payload plus rendered Markdown:

- JSON schemas define payload validity.
- TOML payloads are validated against schemas.
- Markdown renderers create human-readable mail or prompts.
- `specs/comms/templates.toml` maps schema ids to schema paths and renderer paths.
- Sender-side validation is explicit; receiver skills inspect rendered mail semantically and use state or record schemas for their own role action.

The default generated package shape is:

```text
specs/comms/
  comms-overview.md               # Generated human view of message families, routes, reply links, and lifecycle effects.
  templates.toml                  # Registry from short template names and schema ids to schemas/renderers.
  schemas/                        # JSON Schemas for TOML payloads.
    freeform-notice.schema.json   # Generic validated notice for unsupported but loop-relevant content.
    ack.schema.json               # Receipt-only acknowledgement family.
    <message-family>.schema.json
  renderers/                      # Markdown templates used before sending mail through maintained Houmao support.
    freeform-notice.md.j2
    ack.md.j2
    <message-family>.md.j2
```

The creation flow should be:

```text
TOML payload
  -> schema validation
  -> Markdown rendering
  -> mail send through maintained Houmao communication surfaces
```

The same pattern applies to any artifact that must be both structurally recorded and human-readable: define the structured payload, validate it, render it for humans, and preserve the structured data or a stable reference for later audit.

The default templated payload envelope should include `schema_id`, `schema_version`, `payload_id`, `kind`, `run_id`, `plan_revision`, an exchange or handoff id, and `context`. Requests that expect structured replies should include `requested_reply_schema_id` or an explicit equivalent. This lets a receiver know the right reply family without asking the operator to redesign the protocol.

Rendered generated mail should include a fenced `houmao-email-metadata` block, a `Context` section, template-specific human-readable sections, and an explicit reply request section when a reply is expected. The metadata block should carry enough machine-readable identity to connect the rendered mail back to the generated schema and payload lifecycle.

The default generic families are `freeform-notice` and `ack`. `freeform-notice` covers participant-facing or operator-origin content that does not fit a task-specific request/reply template but still needs validated context, requested action, and reply expectation fields. `ack` covers receipt-only acknowledgement without implying a substantive state transition unless another generated contract says so.

When runtime state exists, the harness may expose `email schema|validate|render|apply|query` commands. Those commands inspect schemas, validate TOML payloads, render Markdown, apply loop-local payload lifecycle or mail-caused records, and query recorded payload posture. They must not become mailbox delivery; actual send, read, reply, archive, mailbox binding, and gateway behavior remain delegated to maintained Houmao mail skills.

The maintained skill boundary is part of the default: `houmao-mailbox-mgr` owns mailbox administration, `houmao-agent-email-comms` owns ordinary mail operations, `houmao-process-emails-via-gateway` owns notifier-driven open-mail rounds, `houmao-agent-messaging` owns managed-agent communication routing, and `houmao-agent-gateway` owns gateway lifecycle and posture.

The general lesson is to preserve a schema/render registry for generated communication protocols whenever agents exchange operational work, rather than relying on freeform mail conventions alone. Freeform mail can still exist for operator notices, escalation, or unsupported cases, but ordinary loop work should prefer generated schemas and renderers.

### Defaults And Non-Defaults

Defaults extracted from the reference pattern:
- Houmao mail as the ordinary cross-agent participant transport.
- TOML payloads validated by JSON Schema before Markdown rendering.
- `specs/comms/templates.toml` as the schema/renderer registry.
- a common payload envelope and explicit request-to-reply schema links.
- metadata-bearing rendered Markdown.
- payload lifecycle records when runtime state exists.
- generated mail-received on-event skills triggered by schema id or message family.
- on-tick skills for aggregation, scheduling, reconciliation, timeout, and completion checks.
- maintained Houmao mail skills owning platform mechanics.

Reference-specific details that should not become defaults:
- the exact participant topology from the source plan;
- domain message-family names such as implementation or review requests;
- evidence-field names or domain validation gates;
- the exact scheduling algorithm or completion policy;
- a required SQLite backend or database layout;
- any specific toolchain, evaluation input, artifact type, or specialized domain.

## State And Record Pattern

When a loop needs runtime state, use state storage for compact control-plane bookkeeping and persisted communication for rich prose. State should store ids, refs, scalar gates, ownership markers, transition facts, artifact paths, and ranking or ordering facts. Persisted communication should store context, summaries, directives, rationale, analysis, and other human-readable content.

The generic stateful-loop kernel is:

- plan metadata;
- process state;
- participants or role instances when not fully static elsewhere;
- work items, branches, claims, tasks, or open ends when the loop has goal-directed units;
- handoffs or exchanges;
- communication payload lifecycle;
- attempts, decisions, evidence, and artifacts when the loop needs those facts;
- operator intent events;
- generic events.

Record schemas under `specs/collab/records/` can define controlled payloads such as handoffs, attempts, evidence, decisions, results, and operator intent.

Those task-specific record schemas are extensions. Do not promote a reference plan's evidence, scoring, ranking, or domain tables as default records for unrelated loops.

Generated state contracts should make the valid state space explicit:

- allowed states and statuses;
- valid transitions;
- active ownership invariants;
- mail/evidence/artifact ref expectations;
- operator-intent requirements for override, pause, prune, stop, repair, or recovery actions;
- scheduler and completion queries.

Default backend selection:

- use sqlite when the generated loop has stable entities and transitions that can be expressed as a clear SQL schema;
- include `specs/state/schema.sql` as the authoritative field-level contract for sqlite-backed state;
- include `specs/state/state-overview.md`, `seed.toml` when deterministic initialization is needed, and `invariants.toml` when validation needs named checks;
- use JSONL plus explicit record schemas only for append-only, schema-light, or intentionally denormalized state;
- avoid unstructured ad hoc bookkeeping files.

The general lesson is:

```text
communication carries meaning
state carries compact auditable facts
harness validates and applies narrow records
role skills decide what record should be created
```

## Harness Pattern

The harness should be generated inside the package, not added to Houmao core. Its main job is to manage the loop's data models and dynamic information surfaces.

Harness scripts can use relative symlinks under `harness/refs/` when stable local paths make implementation simpler. Those symlinks point back to authoritative package artifacts such as `../../specs/comms/templates.toml` or `../../specs/state/schema.sql`. If symlinks cannot be created in the current filesystem or permission environment, the harness should use direct relative paths such as `../specs/comms/templates.toml` instead. Do not copy authoritative specs into `harness/`.

Harness-owned data-model mechanics can include:

- communication schemas and template registries;
- collaboration record schemas;
- runtime state schemas, migrations, and invariants;
- payload validation;
- controlled record application;
- compact bookkeeping queries;
- generated view rendering;
- diagnostics and consistency checks.

Harness implementations can rely on common Python libraries when the generated features need them:

- `click` for modular command registration and grouped command-line surfaces;
- `jinja2` for rendering `.md.j2` human-readable mail or prompt templates;
- `jsonschema` for validating communication payloads, record payloads, and command envelopes.

The dependency pattern is Houmao-installed-environment first, caller-selected interpreter second, and optional local-pip-target only for standalone/custom execution. First check whether the intended harness interpreter can import the required libraries. Project declarations such as `pyproject.toml` are useful evidence, but interpreter importability is the proof for that interpreter. If imports fail, generated harness entrypoints should name the missing dependency and guide the caller to install it into the active harness Python environment or use the Python environment associated with the installed Houmao uv tool. Guidance should use uv inspection or refresh commands such as `uv tool list --show-paths --show-python` without hardcoding uv internals.

Generated authoring guidance should tell agents to test the harness after writing it. If a test fails because dependencies are missing, the active interpreter appears wrong, or dependency posture is ambiguous, retry the same test through the Houmao uv-installed environment before rewriting harness logic. If standalone/custom execution is intentionally supported, generate `harness/requirements.txt`, optional `harness/vendor/`, and the caller-managed install command `python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt`. Generated entrypoints that may use `harness/vendor/` should prepend it to `sys.path` before importing local packages. Dependency posture, required packages, interpreter evidence, import-failure guidance, optional standalone install command, and install diagnostics belong in `harness/dependency-posture.toml`, the harness README, the manifest, or an equivalent indexed artifact. These dependency files are harness implementation support; they do not become loop policy or replace contracts under `specs/`.

Harness-owned dynamic information can include:

- objective text and constraints;
- effective policy and configuration values;
- participant and role registries;
- scheduler posture or work ownership;
- completion posture;
- schema explanations;
- current state summaries;
- any other loop-specific value an agent needs during work but should not have baked into static skill text.

A mature harness can expose commands for:

- control status, mode lookup, mode changes, pause/resume/stop records, and manual participant context;
- objective rendering;
- effective policy inspection;
- validation;
- state initialization;
- state query;
- human view rendering;
- ordering or dependency graph export;
- completion checks;
- communication schema, validation, rendering, apply, and query;
- record-type schema, validation, apply, and query.

The harness should use a common machine-readable envelope for agent workflows, collect diagnostics instead of mutating during validation, open runtime state read-only for inspection, and only write through schema-validated `apply` commands.

The default envelope fields are:

- `ok`;
- `command`;
- `run_id` when known;
- `plan_revision` when known;
- `data`;
- `diagnostics`;
- `warnings`.

When generated TOML contracts carry `description` fields, the harness may expose `--explain` or an equivalent explanation view. Explanations help agents use a contract, but the machine contract remains the authority.

The general lesson is that generated role skills should ask the harness for objective, constraints, effective policy, configuration parameters, scheduler posture, schema details, validation diagnostics, and rendered views instead of copying constants into prompts.

## TOML Comment And Description Pattern

Generated TOML contracts should be readable directly and explainable through the harness without parsing comments.

Use plain human-readable comments above each generated section or table-array header:

```toml
# Runtime state backend used by the generated harness.
[state_backend]
kind = "sqlite"
description = "Run-scoped sqlite database used as the live bookkeeping authority."
schema_path = "specs/state/schema.sql"
```

Use `description` fields on records, sections, or non-obvious fields exposed through harness commands. The harness should use these structured `description` values for `--explain` output and include stable source keys or paths. Comments remain useful for human readers, but they are not parsed and are not the explanation source.

## Documentation Pattern

Generated docs are support views. They should start with generated metadata and explain the package for humans, but they must not become source authority. The most important doc pattern is explicit deference: operational truth remains in `specs/`, runtime posture remains in state, and command behavior remains in the harness.

## What This Skill Should Learn

Promote these general patterns over time:

- artifact-indexed generated packages;
- purpose-based `specs/` taxonomy;
- participant roles separate from concrete agents;
- event-scoped and tick-scoped generated skills;
- loop-local operator control skill for lifecycle, mode, manual-step, and recovery routing;
- schema/render registries for mail and other human-readable structured artifacts;
- compact runtime state plus rich persisted communication;
- per-loop harness with data-model management, dynamic lookup, and common machine-readable diagnostics;
- run artifact layouts for payloads, rendered outputs, responses, records, state, logs, and evidence;
- generated Markdown metadata and source-authority disclaimers;
- validation that checks contracts, not only directories.

Do not promote these reference-specific details:

- a particular domain or objective;
- a particular participant topology;
- a particular toolchain or installed domain skill set;
- a particular artifact type;
- a particular evaluation input or evidence gate;
- a particular scheduling algorithm or termination policy;
- a particular JSONL layout or sqlite table layout unless the loop requires it; sqlite is still the default when generated entities and transitions have a clear SQL schema.
