## ADDED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise-v4` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise-v4` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise-v4` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The packaged `houmao-agent-loop-pairwise-v4` skill SHALL be the template-driven successor to `houmao-agent-loop-pairwise-v3` rather than a replacement for the stable pairwise skill, pairwise-v2, or pairwise-v3.

The skill SHALL be manual-invocation-only and SHALL only activate when the user explicitly requests `houmao-agent-loop-pairwise-v4`.

#### Scenario: Reader sees v4 as a new packaged skill
- **WHEN** a reader inspects the packaged loop-skill assets
- **THEN** the inventory includes `houmao-agent-loop-pairwise-v4`
- **AND THEN** the skill is described as the template-driven successor to pairwise-v3

#### Scenario: Generic pairwise requests do not route to v4
- **WHEN** a user asks for generic pairwise loop planning without naming `houmao-agent-loop-pairwise-v4`
- **THEN** the v4 skill does not claim that request
- **AND THEN** the user must explicitly select v4 before the stricter template-first workflow is used

### Requirement: Pairwise-v4 preserves pairwise-v3 lifecycle and workspace runtime posture
The `houmao-agent-loop-pairwise-v4` skill SHALL preserve the pairwise-v3 lifecycle actions: `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, and `hard-kill`.

The `houmao-agent-loop-pairwise-v4` skill SHALL preserve the pairwise-v3 observed states: `authoring`, `initializing`, `ready`, `running`, `paused`, `recovering`, `recovered_ready`, `stopping`, `stopped`, and `dead`.

The v4 skill SHALL require authored workspace contracts with mode `standard` or `custom`.

The v4 skill SHALL preserve pairwise-v3 memo-first initialize, mail-notifier readiness during initialize, mail-first ordinary start, and runtime-owned recovery boundary guidance.

#### Scenario: V4 keeps the v3 runtime model
- **WHEN** a user selects `houmao-agent-loop-pairwise-v4`
- **THEN** the available lifecycle actions match the pairwise-v3 enriched runtime-control surface
- **AND THEN** the stricter v4 behavior appears in authoring and document generation rather than as a new runtime state machine

### Requirement: Pairwise-v4 provides strict generated document templates
The `houmao-agent-loop-pairwise-v4` skill SHALL include packaged document-template guidance for generated bundle files.

Those templates SHALL define required section headers, required section order, and required fields for the generated documents they cover.

At minimum, v4 template guidance SHALL cover:

- canonical `plan.md`,
- role-local `agents/<participant>.md` notes for master/lead, reviewer/evidence-owner, coder/worker, and generic participant roles,
- reporting templates under `<plan-output-dir>/templates/reporting/`,
- bookkeeping templates under `<plan-output-dir>/templates/bookkeeping/`,
- a constraint coverage audit document.

The v4 authoring guidance SHALL instruct the planner to fill the template slots rather than freeform-organize rich task contracts.

When a required template field cannot be filled from known input, the generated file SHALL use an explicit unresolved marker rather than vague prose.

#### Scenario: Planner fills strict templates
- **WHEN** a user asks v4 to author a rich bundle plan
- **THEN** the generated bundle uses the v4 template section headers and required fields
- **AND THEN** missing required information is visibly marked as unresolved instead of being silently omitted or implied

#### Scenario: Agent notes are role-local runtime templates
- **WHEN** v4 generates files under `agents/`
- **THEN** those files contain role-local sections for responsibilities, hard gates, source constraints carried forward, SOP verbs, and related skill posture
- **AND THEN** they are not limited to short reminder bullets when the source task contains role-specific rules

### Requirement: Pairwise-v4 extracts policy-bearing source constraints before writing plan files
The v4 authoring guidance SHALL require a source-constraint extraction pass before drafting generated bundle files.

That pass SHALL inspect the user task note and any explicitly referenced rulebooks or common-contract files that are available in the workspace.

The extraction pass SHALL identify high-salience constraints including:

- policy-bearing emphasized verbs,
- hard gates,
- forbidden actions,
- state schemas,
- phase-transition rules,
- evidence and reporting requirements,
- role-scoped obligations,
- source-transfer or workspace boundaries.

The extraction pass SHALL preserve policy-bearing schema-like verbs when they carry operational meaning, including `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH`.

#### Scenario: Source verbs are preserved when they encode policy
- **WHEN** a rich task note contains a rule such as `**NEVER** mark an open end matured before 3 failed bottleneck-grounded follow-ups`
- **THEN** v4 preserves the `NEVER` policy in the generated source-constraint ledger and relevant role-local surfaces
- **AND THEN** it does not flatten that rule into an ordinary prose suggestion

#### Scenario: Referenced commons are part of extraction
- **WHEN** a task note says to read a common rulebook first
- **THEN** v4 treats that referenced rulebook as a source-contract input when it is available
- **AND THEN** high-salience rules from that source can be carried into the generated bundle

### Requirement: Pairwise-v4 projects extracted constraints into central and runtime surfaces
The v4 authoring guidance SHALL require every extracted high-salience constraint to be projected into at least one generated bundle surface or marked unresolved in the coverage audit.

The canonical `plan.md` SHALL include a central source-contract summary or equivalent carried-forward constraints section that makes operator-critical constraints easy to audit.

Role-scoped constraints SHALL be projected into the relevant `agents/<participant>.md` files.

State schemas SHALL be projected into central plan summaries and, when reusable runtime bookkeeping is needed, into generated bookkeeping templates.

Evidence/reporting constraints SHALL be projected into `reporting.md`, relevant report templates, or role-local reporting gates.

Forbidden actions SHALL remain visible in the central plan and in every role-local note whose recipient could violate that rule.

#### Scenario: Operator can audit carried-forward constraints from plan.md
- **WHEN** a reviewer opens the generated v4 `plan.md`
- **THEN** they can find a central list or table of source constraints carried forward
- **AND THEN** each entry identifies where that constraint was projected in the generated bundle

#### Scenario: Role-specific gates appear in agent notes
- **WHEN** a source task contains a hard gate that applies to one role
- **THEN** the generated note for that role contains the gate in a role-local runtime section
- **AND THEN** unrelated roles are not forced to carry the full text unless they need it for their own duties

### Requirement: Pairwise-v4 writes a constraint coverage audit for rich bundle plans
When v4 authors a rich bundle plan from task notes or referenced rulebooks that contain high-salience constraints, the generated bundle SHALL include a constraint coverage audit document.

The audit SHALL map each extracted high-salience source rule to its central plan location and runtime projection locations.

The audit SHALL mark unresolved or intentionally excluded items explicitly with a reason.

The v4 authoring guidance SHALL require the planner to review the audit before reporting the generated plan as complete.

#### Scenario: Coverage audit catches missing projection
- **WHEN** a source rule is extracted but not projected into any generated runtime surface
- **THEN** the coverage audit marks that rule unresolved
- **AND THEN** the planner does not claim the bundle fully preserved that source rule

#### Scenario: Coverage audit supports source-to-plan review
- **WHEN** an operator compares the generated plan against the original task note
- **THEN** the audit provides a direct mapping from source rules to generated files
- **AND THEN** the operator does not need to diff every support file to know whether a high-salience constraint survived

