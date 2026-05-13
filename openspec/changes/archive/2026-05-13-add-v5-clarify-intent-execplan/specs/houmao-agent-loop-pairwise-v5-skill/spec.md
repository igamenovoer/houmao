## ADDED Requirements

### Requirement: V5 provides distinct intent and execplan clarification subcommands
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose canonical authoring operations named `clarify-intent` and `clarify-execplan`.

The `clarify-intent` operation SHALL focus on user-editable loop intention source.

The `clarify-execplan` operation SHALL focus on generated execplan implementation choices.

The top-level skill routing SHALL distinguish these two operations and route each one to its own authoring page.

The top-level skill MAY treat the natural phrase `clarify intent` as an unambiguous alias for `clarify-intent`, but canonical operation listings and routed pages SHALL use `clarify-intent`.

#### Scenario: Intent clarification routes to intent page
- **WHEN** a user asks v5 to run `clarify-intent`
- **THEN** the top-level skill routes to the intent clarification page
- **AND THEN** that page works from `<loop-dir>/intention/` as source authority

#### Scenario: Execplan clarification routes to execplan page
- **WHEN** a user asks v5 to run `clarify-execplan`
- **THEN** the top-level skill routes to the execplan clarification page
- **AND THEN** that page works from `<loop-dir>/execplan/` as generated implementation authority

### Requirement: V5 clarification uses a shared structured clarification protocol
The packaged v5 skill SHALL include a runtime-readable clarification protocol reference page under `subskills/reference/`.

Clarification operation pages SHALL read the shared clarification protocol before asking clarification questions.

Clarification operation pages SHALL read `runtime-mail-model.md` before clarifying any mail-driven loop behavior.

The shared clarification protocol SHALL require the invoking agent to read relevant source artifacts before asking questions.

The shared clarification protocol SHALL require an internal coverage scan before asking questions.

The shared clarification protocol SHALL require candidate questions to be prioritized by impact and uncertainty.

The shared clarification protocol SHALL allow at most five accepted clarification questions per session.

The shared clarification protocol SHALL require exactly one question at a time.

The shared clarification protocol SHALL require each question to be answerable by either a short multiple-choice selection or a constrained short answer.

The shared clarification protocol SHALL require a recommended or suggested answer with concise reasoning when the available context supports one.

The shared clarification protocol SHALL require accepted answers to be recorded immediately and reflected in the appropriate source artifacts.

The shared clarification protocol SHALL require validation after each accepted answer so obsolete contradictions are removed and the clarified ambiguity is not left unresolved.

The shared clarification protocol SHALL require a final coverage summary with clear, resolved, deferred, and outstanding categories.

#### Scenario: Clarification scans before asking
- **WHEN** a clarification operation starts
- **THEN** it reads the required source artifacts and reference pages
- **AND THEN** it builds an internal coverage map before asking the first question

#### Scenario: Clarification asks one high-impact question
- **WHEN** the internal scan finds multiple ambiguity candidates
- **THEN** the operation chooses the highest-impact unresolved candidate
- **AND THEN** it asks only one question before waiting for the user's answer

#### Scenario: Accepted answer is integrated immediately
- **WHEN** the user accepts, edits, or supplies a valid answer
- **THEN** the operation records the accepted answer
- **AND THEN** it updates the affected source artifacts before asking another question

### Requirement: V5 intent clarification scans loop intent coverage before questioning
The `clarify-intent` operation SHALL read current intention source, project context when present, and existing intent ADRs when present before asking questions.

The `clarify-intent` operation SHALL scan intent coverage categories for at least:

- objective, non-goals, and completion signals;
- participant roles, authorities, and handoff rights;
- collaboration topology and work-item lifecycle;
- mail/message families at intent level;
- on-event and on-tick responsibilities;
- state/bookkeeping needs;
- operator controls and recovery posture;
- workspace, artifact, and evidence expectations;
- project integration context;
- terminology and explicit omissions.

The `clarify-intent` operation SHALL prioritize questions that materially affect generated process, contracts, runtime safety, scheduling, recovery, validation, or acceptance.

The `clarify-intent` operation SHALL avoid asking low-impact local wording or formatting questions when higher-impact loop logic remains unclear.

Accepted `clarify-intent` answers SHALL be recorded under the loop's intent ADR area and reflected in `intention/` Markdown.

The `clarify-intent` operation SHALL NOT directly edit generated `execplan/` artifacts.

#### Scenario: Intent clarification finds core loop ambiguity
- **WHEN** intention source states participants but not completion authority
- **THEN** `clarify-intent` treats completion authority as a high-impact ambiguity
- **AND THEN** it asks a targeted question before asking local wording or file-organization questions

#### Scenario: Intent clarification updates intention source only
- **WHEN** the user accepts an intent clarification answer
- **THEN** the answer is recorded in an intent ADR
- **AND THEN** the relevant intention Markdown is updated
- **AND THEN** generated `execplan/` files are not directly edited by `clarify-intent`

### Requirement: V5 execplan clarification scans generated implementation coverage before questioning
The `clarify-execplan` operation SHALL require an existing generated `<loop-dir>/execplan/` package.

The `clarify-execplan` operation SHALL read relevant generated execplan artifacts before asking questions, including process specs, derived contracts, harness surfaces, generated skills, agent bindings, manifest, docs, and prior execplan ADRs when present.

The `clarify-execplan` operation SHALL scan generated implementation coverage categories for at least:

- process phases, events, handoffs, ticks, terminal posture, and recovery posture;
- mail schemas, renderers, reply links, ack/result/error families, and payload lifecycle;
- state schema, transitions, invariants, ownership, backend choice, and repair posture;
- harness commands for initialization, query, validation, record apply, rendering, and explain output;
- generated skill triggers, bounded procedures, stop points, and tick placement;
- agent bindings, notifier prompts, support skills, workspace policy, and memo posture;
- run artifacts, evidence refs, validation coverage, manifest coherence, and generated docs;
- platform boundary compliance and no in-chat waiting.

The `clarify-execplan` operation SHALL ask only about implementation decisions that are unclear, unjustified by intention or defaults, contradictory, or likely to affect runtime correctness.

Accepted `clarify-execplan` answers SHALL be recorded under `<loop-dir>/execplan/adrs/` and reflected in the affected generated execplan artifacts.

When an accepted answer affects an upstream generation stage, `clarify-execplan` SHALL update or flag all downstream affected artifacts according to the generation pipeline.

The `clarify-execplan` operation SHALL NOT rewrite editable intention source unless it discovers that the generated ambiguity comes from missing or contradictory intention source; in that case it SHALL report the issue and direct the user to `clarify-intent` or an intention edit.

#### Scenario: Execplan clarification finds missing reply handling
- **WHEN** generated mail contracts define a result request but no reply expectation, timeout, or reconciliation tick
- **THEN** `clarify-execplan` treats the missing handling as a high-impact implementation ambiguity
- **AND THEN** it asks a targeted question before asking about local file wording

#### Scenario: Execplan clarification records generated implementation decision
- **WHEN** the user accepts an execplan clarification answer
- **THEN** the answer is recorded under `<loop-dir>/execplan/adrs/`
- **AND THEN** the affected generated specs, harness, skills, agents, docs, manifest, or validation notes are updated or flagged according to the generation pipeline

#### Scenario: Execplan clarification detects intent source gap
- **WHEN** an implementation ambiguity cannot be resolved without changing the loop's intended behavior
- **THEN** `clarify-execplan` reports that the issue belongs in intention source
- **AND THEN** it does not silently invent intention policy inside generated artifacts
