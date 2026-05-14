## ADDED Requirements

### Requirement: V5 generation provides a generic default execplan scaffold
The packaged skill SHALL treat a reusable generated execplan scaffold as the default target when generating `<loop-dir>/execplan/` from intention source.

The default scaffold SHALL include generated artifact metadata and a manifest-indexed package with the existing top-level areas `specs/`, `skills/`, `agents/`, `harness/`, and `docs/`.

The default `specs/` area SHALL provide places for objective contracts, collaboration contracts, communication contracts, runtime state contracts, workspace contracts, and participant contracts when the loop needs those concerns.

The generator SHALL allow irrelevant default areas or files to be omitted and task-specific areas or files to be added when the intention source or clarification decisions justify that shape.

#### Scenario: Generated execplan has reusable package contracts
- **WHEN** the skill generates an execplan for a loop whose intention does not override the package shape
- **THEN** the generated execplan includes a manifest-indexed package with `specs/`, `skills/`, `agents/`, `harness/`, and `docs/`
- **AND THEN** generated specs separate objective, collaboration, communication, state, workspace, and participant concerns when those concerns apply

#### Scenario: Simple loop can omit unnecessary default files
- **WHEN** the current intention source describes a loop that does not need durable runtime state or a generated workspace contract
- **THEN** the generated execplan may omit those specific default files
- **AND THEN** the manifest and generated docs make the omission explicit enough for validation and later extension

### Requirement: V5 defaults participant and agent bindings to separated identities
The packaged skill SHALL guide generated execplans to separate participant role templates, participant role instances, and concrete Houmao agent bindings.

Generated participant contracts SHALL define stable loop participant identities and responsibilities without requiring a fixed topology or fixed role names.

Generated agent bindings SHALL bind concrete Houmao agents to participant instances and identify prompt source, installed generated skills, maintained support skills, skill installation mode, memo seed policy, and workspace policy when those facts apply.

#### Scenario: Participant identity is not the concrete process
- **WHEN** the skill generates participant and agent material for a loop
- **THEN** participant specs define stable role instances for the loop
- **AND THEN** agent bindings separately map concrete Houmao agents to those participant instances

#### Scenario: Topology remains intention-derived
- **WHEN** the intention source defines a custom participant topology
- **THEN** the generated participant and agent bindings follow that topology
- **AND THEN** the packaged skill does not force a built-in coordinator, reviewer, or worker count

### Requirement: V5 defaults stateful loops to a minimal runtime bookkeeping kernel
When a generated loop needs durable runtime state, the packaged skill SHALL guide the execplan to include a minimal loop-local bookkeeping kernel or an explicitly equivalent generated contract.

The default bookkeeping kernel SHALL cover plan metadata, process state, handoffs or exchanges, structured communication payload lifecycle, operator intent events, and generic events.

Task-specific records, evidence models, scoring models, and domain tables SHALL be generated only from intention source or clarification decisions.

#### Scenario: Stateful loop gets generic bookkeeping
- **WHEN** the intention source implies durable handoffs, scheduling decisions, recovery, or audit
- **THEN** the generated execplan includes generic loop-local bookkeeping contracts for process state, exchanges, payload lifecycle, operator intent, and events
- **AND THEN** task-specific records are added only as generated extensions

#### Scenario: Stateless loop does not inherit domain tables
- **WHEN** the intention source describes a lightweight loop without domain records
- **THEN** the generated execplan does not import task-specific record tables from examples
- **AND THEN** validation accepts the absence of those task-specific tables

### Requirement: V5 defaults generated harnesses to narrow loop-local services
The packaged skill SHALL guide generated execplans to include a plan-local harness when the loop needs validation, dynamic lookup, rendering, record application, or state queries.

The generated harness SHALL be scoped to loop-local contracts such as objective rendering, policy explanation, communication payload schema inspection, payload validation, Markdown rendering, state query, invariant validation, completion checks, and controlled record application.

The generated harness SHALL NOT own Houmao platform operations such as mailbox delivery, mailbox administration, managed-agent launch, gateway discovery, prompt transport, memory management, or workspace creation.

Harness command output intended for agent use SHALL default to a structured envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings.

#### Scenario: Agent asks harness for dynamic loop facts
- **WHEN** a generated role skill needs objective, policy, state, route, schema, or completion facts
- **THEN** it uses the generated harness or generated contract surface to retrieve those facts
- **AND THEN** it does not rely on static copied values embedded in role prose

#### Scenario: Harness boundary excludes platform mechanics
- **WHEN** generated execution needs mailbox transport, agent launch, gateway posture, memory updates, or workspace creation
- **THEN** the generated execution guidance routes that work to maintained Houmao skills or supported CLI surfaces
- **AND THEN** the generated harness remains responsible only for loop-local data mechanics

### Requirement: V5 defaults generated role skills to bounded event and tick handlers
The packaged skill SHALL guide generated execplans to create generated role skills that are scoped by role and by event, tick, or operator lifecycle action.

Generated on-event skills SHALL define their trigger, owning participant role, required context lookup, role-owned action, outgoing communication behavior, record effects, archive behavior when mail is involved, and stopping point.

Generated on-tick skills SHALL be used for scheduling, reconciliation, timeout, completion, or "what happens next" behavior that does not belong to one incoming event.

Generated tick skills SHALL inspect current dynamic state, perform one bounded applicable action or report no action, and stop.

#### Scenario: Mail event handler is bounded
- **WHEN** a generated participant receives a loop-defined mail family that has an on-event skill
- **THEN** the on-event skill handles that received message family for the owning role
- **AND THEN** it stops after the bounded event response instead of recursively driving unrelated loop phases

#### Scenario: Scheduler behavior uses a tick handler
- **WHEN** a loop requires scheduling or reconciliation after one or more events
- **THEN** the generated execplan represents that responsibility as an on-tick skill for the owning role
- **AND THEN** the tick handler performs at most one scheduling or reconciliation pass before stopping

### Requirement: V5 defaults workspace and run artifacts to auditable generated contracts
When a generated loop needs agent workspaces, the packaged skill SHALL guide the execplan to generate workspace contracts that can be consumed by `houmao-utils-workspace-mgr` or equivalent maintained workspace surfaces.

The default workspace contract SHALL identify launch cwd, per-agent work roots, per-agent note or knowledge paths, writable temporary artifact paths, shared resources, and read/write rules when those facts apply.

When a generated loop executes with durable artifacts, the packaged skill SHALL guide the runtime layout to preserve run-local payloads, rendered outputs, send or reply responses, record files, state files, logs, and evidence under a run directory such as `<loop-dir>/runs/<run-id>/` or an explicitly generated equivalent.

#### Scenario: Workspace defaults become manager input
- **WHEN** generated execution prepares workspaces for participants
- **THEN** the execplan provides workspace facts suitable for maintained workspace planning and verification
- **AND THEN** generated skills do not perform ad hoc workspace creation when a maintained workspace surface applies

#### Scenario: Run directory supports audit and recovery
- **WHEN** a generated loop records structured payloads, rendered messages, replies, records, state, or evidence during execution
- **THEN** those artifacts are preserved under the generated run artifact layout
- **AND THEN** status, validation, recovery, and human review can refer to those artifacts without depending only on live mailbox state
