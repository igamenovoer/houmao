# houmao-agent-loop-pro-skill Specification

## Purpose
TBD - created by archiving change add-houmao-agent-loop-pro. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged manual `houmao-agent-loop-pro` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pro` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pro` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The packaged `houmao-agent-loop-pro` skill SHALL be manual-invocation-only. It SHALL only activate when the user explicitly requests `houmao-agent-loop-pro` or an explicitly named pro loop operation.

The packaged skill SHALL describe itself as a professional loop authoring and execution skill that supports both pairwise-tree and generic-graph topology modes.

#### Scenario: User explicitly invokes pro
- **WHEN** a user explicitly asks to use `houmao-agent-loop-pro`
- **THEN** the packaged pro skill is the correct Houmao-owned entrypoint
- **AND THEN** it presents a topology-aware loop authoring and execution workflow

#### Scenario: Generic loop request does not auto-route to pro
- **WHEN** a user asks generically to plan or run an agent loop without naming `houmao-agent-loop-pro`
- **THEN** the pro skill does not claim the request by default
- **AND THEN** the user must explicitly select pro before pro-specific files or operations are created

### Requirement: Pro skill is derived from the pairwise-v5 generated execplan workflow
The `houmao-agent-loop-pro` skill SHALL preserve the pairwise-v5 style split between editable intention material and generated execplan material.

The skill SHALL keep `<loop-dir>/intention/` as editable source material.

The skill SHALL keep `<loop-dir>/execplan/` as generated operational material.

The skill SHALL preserve the staged generation model in which process specs are generated before derived contracts, harness surfaces, generated skills, agent bindings, and final support docs.

The skill SHALL NOT present itself as `houmao-agent-loop-pairwise-v5` or mention v5 lineage in user-facing skill body text.

#### Scenario: Pro initializes a loop directory
- **WHEN** a user invokes `houmao-agent-loop-pro init` with a selected `<loop-dir>`
- **THEN** the skill creates or updates editable intention material under `<loop-dir>/intention/`
- **AND THEN** it does not create generated runtime behavior outside the selected loop directory

#### Scenario: Pro generates execplan artifacts in order
- **WHEN** a user invokes a pro execplan generation command
- **THEN** the generated process spec is the first generated authority
- **AND THEN** later generated contracts, harness surfaces, generated skills, agent bindings, and docs derive from that process spec

### Requirement: Pro supports explicit topology modes
Generated pro execplans SHALL declare exactly one topology mode for the loop unless generation is explicitly blocked on unresolved topology intent.

Supported topology modes SHALL include:

- `pairwise-tree`, for tree-shaped or forest-shaped local-close execution;
- `generic-graph`, for directed graph execution that can include cycles and non-tree communication routes.

The selected topology mode SHALL be recorded in generated process material and in generated topology contracts when topology contracts are emitted.

The selected topology mode SHALL drive communication, state, harness, generated-skill, and validation requirements.

#### Scenario: Pairwise tree mode is selected
- **WHEN** intention source or accepted clarification decisions select pairwise local-close execution
- **THEN** the generated execplan records `pairwise-tree` as the topology mode
- **AND THEN** the generated contracts apply pairwise-tree routing and validation rules

#### Scenario: Generic graph mode is selected
- **WHEN** intention source or accepted clarification decisions select directed graph execution with cycles or non-tree routes
- **THEN** the generated execplan records `generic-graph` as the topology mode
- **AND THEN** the generated contracts apply generic-graph context-consideration and validation rules

### Requirement: Pairwise-tree mode enforces local-close execution
In `pairwise-tree` mode, each execution edge SHALL represent a local-close upstream/downstream handoff.

In `pairwise-tree` mode, a downstream participant SHALL return its result or reply to its immediate upstream participant unless the generated process explicitly marks an operator-control or terminal-report exception.

In `pairwise-tree` mode, generated execution subgraphs SHALL be trees or forests.

In `pairwise-tree` mode, generated plans SHALL NOT allow a downstream result to bypass its immediate upstream as normal participant result flow.

#### Scenario: Worker replies to immediate upstream
- **WHEN** a generated pairwise-tree loop has an edge from participant `A` to participant `B`
- **THEN** participant `B` replies to participant `A` for that edge's local-close result
- **AND THEN** the generated communication contract does not route `B`'s normal result to a distant ancestor

#### Scenario: Pairwise result bypass is rejected
- **WHEN** a pairwise-tree generated topology routes a participant result around the immediate upstream without a recorded exception
- **THEN** pro execplan validation reports the topology as invalid
- **AND THEN** it requires the generated topology or selected mode to be revised

### Requirement: Pro normalizes non-tree pairwise intent without inventing participants
When intention source describes pairwise behavior but includes a non-tree closed loop, the pro skill SHALL NOT silently generate cyclic pairwise execution.

The pro skill SHALL either clarify whether the user wants `generic-graph` mode or normalize the intended pairwise behavior into local-close tree or forest execution.

When normalizing, the pro skill SHALL choose an existing participant as the relay, root, or cycle breaker.

The pro skill SHALL NOT create a new synthetic participant solely to break a pairwise cycle.

The normalization decision SHALL be recorded in generated process or topology artifacts, and in ADRs when the operation records decisions.

#### Scenario: Pairwise cycle is normalized through an existing participant
- **WHEN** intention source asks for pairwise behavior shaped like `A -> B -> C -> A`
- **AND WHEN** the accepted decision is to keep pairwise-tree mode
- **THEN** the generated topology breaks the closed loop into local-close tree-shaped execution using one of `A`, `B`, or `C` as the relay, root, or cycle breaker
- **AND THEN** the generated artifacts record which existing participant owns that normalization role

#### Scenario: Ambiguous cycle is clarified
- **WHEN** intention source describes `A -> B -> C -> A` without saying whether it is a true directed loop or a local-close pairwise chain
- **THEN** `clarify-intent` or `clarify-execplan` asks a topology-mode question before finalizing generated topology
- **AND THEN** generation does not silently choose cyclic pairwise execution

### Requirement: Generic-graph mode considers task-specific predecessor context
In `generic-graph` mode, generated communication contracts SHALL support directed graph routes that can include cycles and non-tree downstream communication.

In `generic-graph` mode, execplan generation SHALL consider whether each downstream route or message family needs selected predecessor information from upstream participants.

When selected predecessor information is needed, generated communication contracts SHALL define what to carry or reference, such as predecessor message refs, ancestor refs, artifact refs, commit refs, state refs, summaries, required context keys, or current-hop deltas.

When selected predecessor information is not needed for a route or message family, generated communication contracts MAY omit carried upstream context and SHOULD make that omission explicit in the process, communication, manifest, generated docs, or validation notes when the route is non-obvious.

Generic-graph handoff schemas SHALL still include the fields needed for the generated loop's own routing and validation, such as run identity, work item identity, edge identity, sender, receiver, expected receiver action, and reply or forward policy when those concepts apply.

Rendered generic-graph mail SHALL include a human-readable context section only when the generated communication contract selects carried predecessor context for that message family.

#### Scenario: Generic handoff carries selected predecessor context
- **WHEN** participant `B` sends a generic-graph handoff to participant `C` based on prior information from participant `A`
- **AND WHEN** the generated execplan says `C` needs selected `A` context
- **THEN** the handoff payload includes the selected references or summaries needed for `C` to understand that relevant `A` context
- **AND THEN** `C` is not required to guess which distant upstream mail, artifact, branch, or state entry matters

#### Scenario: Generic handoff omits unneeded predecessor context
- **WHEN** a generated generic-graph route does not require predecessor context for the downstream participant to act
- **THEN** the generated communication contract may omit upstream context fields for that route
- **AND THEN** validation does not fail solely because no predecessor context is carried

#### Scenario: Generic rendered mail is readable when context is selected
- **WHEN** a generic-graph handoff is rendered as Markdown mail
- **AND WHEN** the generated contract selects carried predecessor context
- **THEN** the rendered mail contains a readable carried-context section
- **AND THEN** the selected structured metadata remains available for schema validation and harness processing

### Requirement: Pro generated templated mail is schema-typed
Generated pro execplans SHALL treat each templated participant mail family as a schema-typed event.

For each templated participant mail family, generated communication contracts SHALL define a stable `schema_id` that acts as the loop-local mail type.

Generated communication contracts SHALL include a template registry that maps each template name to its `schema_id`, JSON Schema path, and Markdown renderer path.

Generated templated mail authoring guidance SHALL use the flow: TOML payload, schema validation, Markdown rendering, then Houmao mail delivery.

Generated schemas SHALL include constant or otherwise validation-visible fields for `schema_id`, `schema_version`, and mail `kind` when those concepts apply.

Generated schemas SHALL include run, plan revision, payload, handoff, exchange, route, reply, or result identifiers when those identifiers are needed for the loop's routing and bookkeeping.

#### Scenario: Template registry maps schema to renderer
- **WHEN** a pro execplan emits a templated participant mail family
- **THEN** generated communication specs include a registry entry with the template name, schema id, schema path, and renderer path
- **AND THEN** generated harness or skill guidance can resolve the mail family from either the template name or schema id

#### Scenario: Outgoing templated mail is validated before render
- **WHEN** a generated skill authors templated outgoing participant mail
- **THEN** the skill guidance routes payload creation through schema validation before rendering
- **AND THEN** the rendered Markdown is the body sent through maintained Houmao mail support

### Requirement: Pro rendered templated mail includes an in-body schema metadata header
Generated Markdown renderers for templated pro mail SHALL include a parseable in-body metadata header near the start of the rendered mail.

The normal metadata header SHALL be a fenced `houmao-email-metadata` block unless a generated execplan records an equivalent parseable in-body metadata block name.

The metadata header SHALL include `schema_id`, `schema_version`, `kind`, `run_id`, `plan_revision`, and any payload, handoff, exchange, route, reply, or result identifiers that the generated mail family needs for event dispatch and bookkeeping.

The metadata header SHALL be human-visible in the mail body so an agent and a notifier prompt can identify the mail type without relying on hidden transport headers.

#### Scenario: Rendered mail exposes schema id
- **WHEN** a templated participant mail body is rendered
- **THEN** the rendered Markdown starts with or otherwise prominently includes a parseable metadata block containing `schema_id`
- **AND THEN** the schema id identifies the generated mail family for event-skill dispatch

#### Scenario: Transport headers are not required for type detection
- **WHEN** a generated on-event skill receives a rendered templated mail body
- **THEN** the skill can identify the mail type from the in-body metadata header
- **AND THEN** it does not require hidden email transport headers to choose the event handler

### Requirement: Pro generated on-event skills trigger from detected mail schema ids
Generated pro on-event skills for templated mail SHALL state their trigger in terms of the expected mail `schema_id`.

Generated notifier prompt or agent-binding guidance SHALL direct agents to inspect or use the detected in-body metadata `schema_id` to choose the matching generated on-event skill when processing templated mail.

Generated event skills MAY assume sender-side schema validation for ordinary templated mail and focus on semantic inspection, role-owned action, state updates, and outgoing replies.

Generated repair, operator-origin, freeform, or unknown-mail skills SHALL handle mail that lacks a recognized templated schema id when the generated loop needs those paths.

#### Scenario: Event skill trigger names schema id
- **WHEN** a generated event skill handles a templated participant request or reply
- **THEN** its trigger section names the exact expected `schema_id`
- **AND THEN** the skill is not triggered only by ambiguous subject text or sender identity

#### Scenario: Unknown schema follows fallback path
- **WHEN** an agent receives mail without a recognized generated schema id
- **THEN** generated guidance uses a freeform, operator-origin, unknown-mail, or repair path when that path exists
- **AND THEN** it does not force the mail into an unrelated schema-typed event skill

### Requirement: Generic-graph mode records cycle control and dedupe contracts
In `generic-graph` mode, generated execplans SHALL define how cyclic or repeat visits are bounded, deduplicated, and terminated.

Generated state or record contracts SHALL include compact facts sufficient to track work item lineage, visited nodes or edges, cycle iteration counts, active ownership, message refs, and terminal posture when those concepts apply.

Generated process specs SHALL describe the stopping condition for each true directed loop.

Generated validation SHALL reject generic-graph loops that have cycles but no explicit termination, dedupe, or repeat-visit policy.

#### Scenario: Cyclic generic graph has termination rules
- **WHEN** a generic-graph topology contains a cycle
- **THEN** generated process and state contracts record the termination or stopping condition for that cycle
- **AND THEN** generated validation can identify whether the cycle has a bounded or otherwise explicit repeat policy

#### Scenario: Cyclic generic graph without dedupe is invalid
- **WHEN** a generated generic-graph execplan contains a cyclic route but no dedupe or repeat-visit contract
- **THEN** `validate-execplan` reports the generated plan as invalid
- **AND THEN** it identifies the missing cycle-control contract

### Requirement: Pro generates topology and task-selected context contracts in the execplan package
When a pro loop needs topology contracts, generated files SHALL live under the generated execplan specs area.

The normal topology contract location SHALL be `<loop-dir>/execplan/specs/collab/topology/`.

Generated topology material SHALL include a human-readable graph explanation and a machine-readable topology contract when machine validation or harness queries need it.

When predecessor-context carrying is selected by the generated execplan, generated communication or collaboration contracts SHALL define the selected context fields, rendering expectations, and validation behavior.

When predecessor-context carrying is intentionally omitted for a generic-graph route or message family, generated artifacts SHALL leave enough explanation for validators and future revisers to understand that omission as a task-specific decision rather than an accidental missing field.

Generated topology and context files SHALL be indexed or explained in `manifest.toml`, generated docs, or validation notes.

#### Scenario: Topology package is generated
- **WHEN** a pro execplan includes non-trivial participant routes
- **THEN** `<loop-dir>/execplan/specs/collab/topology/` contains generated topology contract material
- **AND THEN** the manifest or generated docs point to that topology material

#### Scenario: Context posture is generated
- **WHEN** a pro execplan uses `generic-graph` mode
- **THEN** generated specs record whether each relevant route or message family carries predecessor context
- **AND THEN** generated validation can distinguish required selected context fields from intentional context omission

### Requirement: Pro generated harnesses validate topology and selected context when required
Generated pro harnesses SHALL expose loop-local validation and query surfaces for topology and context contracts when the generated loop needs them.

For `pairwise-tree` mode, generated harness validation SHALL be able to detect direct non-tree participant cycles unless an accepted normalization decision has converted them into local-close tree or forest execution.

For `generic-graph` mode, generated harness validation SHALL be able to validate task-selected context fields, predecessor refs, lineage facts, cycle-control fields, and state refs when those concepts are emitted.

Generated harnesses SHALL store or query compact context and topology facts through generated state or record contracts rather than copying full mail bodies into state.

#### Scenario: Harness validates pairwise-tree topology
- **WHEN** a generated pairwise-tree topology contains a direct participant cycle
- **THEN** the generated harness validation reports the cycle as invalid unless a recorded normalization has removed it from execution topology
- **AND THEN** the validation points to the topology contract that needs revision

#### Scenario: Harness validates selected generic context payload
- **WHEN** a generated generic-graph handoff payload omits a predecessor context field required by that generated execplan
- **THEN** the generated harness validation rejects the payload
- **AND THEN** it reports the missing field or context key

### Requirement: Pro generated skills preserve topology and selected context semantics
Generated pro on-event and on-tick skills SHALL read the selected topology mode from generated specs, state, or harness output rather than inferring it from static prose.

In `pairwise-tree` mode, generated participant skills SHALL return normal results to immediate upstream participants.

In `generic-graph` mode, generated participant skills SHALL preserve selected carried context when the generated execplan requires forwarding or replying with predecessor context.

Generated skills SHALL finish one bounded event or tick pass and then stop, following Houmao's notifier-prompt-driven mail loop model.

#### Scenario: Pairwise generated skill replies upstream
- **WHEN** a generated pairwise-tree on-event skill completes a downstream action
- **THEN** it sends the expected reply to the immediate upstream participant
- **AND THEN** it does not route the result to a distant participant unless the generated contract defines an exception

#### Scenario: Generic generated skill forwards selected carried context
- **WHEN** a generated generic-graph on-event skill forwards work to the next participant
- **AND WHEN** the generated execplan requires selected carried context for that outgoing communication
- **THEN** it includes the selected context bundle or context refs
- **AND THEN** it records or references the handoff through the generated harness when the execplan defines that surface

### Requirement: Pro does not require a master participant by default
The `houmao-agent-loop-pro` skill SHALL NOT require every generated loop to have a master, lead, coordinator, or root owner.

The generated execplan SHALL name acceptance authority, start authority, scheduler or tick ownership, relay ownership, root ownership, and terminal reporting authority only when those concepts are required by intention source or accepted clarification decisions.

If a generated loop needs a central owner, the generated contracts SHALL state that owner explicitly.

If a generated loop does not need a central owner, generated lifecycle and communication contracts SHALL still define how start, completion, stop, recovery, and operator control work.

#### Scenario: Loop with no central master is valid
- **WHEN** intention source defines a generic-graph loop with decentralized participant responsibilities and explicit operator-control handling
- **THEN** the pro skill can generate an execplan without adding a master participant
- **AND THEN** generated validation does not fail solely because no master role exists

#### Scenario: Loop with a chosen coordinator records it explicitly
- **WHEN** intention source or accepted clarification decisions choose a coordinator participant
- **THEN** the generated execplan records that coordinator's authority and boundaries
- **AND THEN** the coordinator role is not treated as an implicit requirement for other pro loops

### Requirement: Pro clarification prioritizes topology, communication context choices, and objective semantics
The pro `clarify-intent` and `clarify-execplan` guidance SHALL prioritize questions that affect objective semantics, topology mode, participant communication, predecessor-context choices, loop process, termination, state, workspace, and validation.

The pro clarification guidance SHALL show high-level Mermaid diagrams for agent architecture and loop structure before the first intent clarification question when enough source material exists.

The pro clarification guidance SHALL avoid low-impact wording or file-organization questions while topology mode, communication context needs, loop process, objective, or termination remains unclear.

#### Scenario: Clarification asks topology-mode question early
- **WHEN** intention source can plausibly mean either pairwise-tree or generic-graph execution
- **THEN** pro clarification asks about topology mode before asking low-impact local file questions
- **AND THEN** accepted answers are recorded in intention material or ADRs according to the operation

#### Scenario: Clarification visualizes loop shape
- **WHEN** intention source identifies participants or route candidates
- **THEN** pro clarification shows a high-level Mermaid architecture or loop-structure diagram
- **AND THEN** unknown topology or context details are marked as unknown rather than invented

### Requirement: Pro prepare-agents routes persisted agent preparation through agent-definition
The pro `prepare-agents` guidance SHALL route specialist, easy-profile, raw-profile, credential-defaulting, and pre-launch definition preparation through the canonical `houmao-agent-definition` skill.

The pro `prepare-agents` guidance SHALL default to `houmao-agent-definition create-agent-fast-forward` when a participant may need both specialist and easy profile preparation.

The pro `prepare-agents` guidance SHALL use `houmao-agent-definition profiles`, `specialists`, or `raw-profiles` only when that narrower route matches the generated execplan or operator intent.

The pro `prepare-agents` guidance SHALL treat `houmao-mgr project easy ...` as the underlying CLI surface owned by `houmao-agent-definition`, not as loop-local agent-preparation logic.

#### Scenario: Participant profile creation uses agent-definition
- **WHEN** `prepare-agents` needs to prepare one participant's specialist and easy profile
- **THEN** it routes the work through `houmao-agent-definition create-agent-fast-forward`
- **AND THEN** it records the returned specialist, profile, tool, credential, launch, and generated-skill facts for later stages

#### Scenario: Pro does not duplicate credential defaulting
- **WHEN** participant agent preparation lacks explicit tool or credential input
- **THEN** `prepare-agents` relies on `houmao-agent-definition` credential routing
- **AND THEN** it does not implement its own credential selection from Houmao credential stores

### Requirement: Pro system-input questions distinguish required and optional loop runtime inputs
The packaged `houmao-agent-loop-pro` skill SHALL use required/optional input labels when asking users for Houmao loop system-operation values.

Those labeled questions SHALL apply to loop directory selection, project context roots, generated artifact locations, workspace preparation targets, agent-definition preparation inputs, validation targets, launch targets, operator-control targets, mail-notifier posture, lifecycle mode, and other Houmao runtime mechanics.

The pro skill SHALL NOT impose required/optional labels on user-task intent questions about objectives, acceptance criteria, domain constraints, participant reasoning, or business semantics unless the specific question asks for Houmao runtime behavior.

#### Scenario: Init asks for loop directory as required input
- **WHEN** `houmao-agent-loop-pro init` needs the user to choose an output loop directory
- **THEN** the skill asks with a required section that names the loop directory
- **AND THEN** it includes an optional section for project root, project context hints, naming preferences, or states that no optional input is needed

#### Scenario: Preparation asks for system blockers with optional defaults
- **WHEN** `prepare-agents`, `prepare-workspace`, `validate-loop`, or `launch-agents` lacks a Houmao system input needed to proceed
- **THEN** the skill asks with required inputs separated from optional modifiers
- **AND THEN** the optional section identifies defaults, skip behavior, or manual alternatives when they exist

#### Scenario: Intent clarification remains domain-focused
- **WHEN** `clarify-intent` asks about objective ambiguity, acceptance semantics, participant responsibilities, or task-specific loop behavior
- **THEN** the question is not required to use required/optional system-input labels
- **AND THEN** the clarification flow still uses required/optional labels if it asks for a Houmao runtime setting such as topology mode, workspace sharing, mail-notifier mode, or lifecycle control behavior
