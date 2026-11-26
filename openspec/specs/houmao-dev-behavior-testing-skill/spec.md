# houmao-dev-behavior-testing-skill Specification

## Purpose
Developers use the behavior-testing skill to qualify system-skill activation, routing, actor boundaries, and effects against a committed case catalog. Isolated runs preserve evidence and report repeated outcomes by verdict dimension.
## Requirements

### Requirement: Behavior qualification is a manual development skill
The repository SHALL provide `skillset/dev/houmao-dev-behavior-testing` as a host-discoverable development skill with top-level `SKILL.md` and `agents/openai.yaml`.

The skill MUST require explicit invocation and MUST NOT be included in the packaged Houmao system-skill manifest, admin pack, agent pack, or ordinary user installation lifecycle.

#### Scenario: Maintainer explicitly invokes behavior qualification
- **WHEN** a maintainer invokes `houmao-dev-behavior-testing` for a system-skill behavior case
- **THEN** the skill exposes its planning, execution, adjudication, reporting, catalog, and suite workflows
- **AND THEN** it does not present itself as a runtime Houmao system skill

#### Scenario: Managed system-skill installation remains unchanged
- **WHEN** Houmao resolves an admin pack or agent pack
- **THEN** neither development testing skill appears in the resolved install set

### Requirement: Behavior qualification follows the Imsight complex-procedure format
The skill SHALL use a concise router with a numbered `## Workflow`, a freeform planning fallback, standard object-style invocation notation, and concise `DO NOT` guardrails.

It SHALL expose procedural subcommands `plan-run`, `execute-case`, `adjudicate-case`, and `report-run`; helper subcommands `snapshot-context` and `collect-evidence`; and misc subcommands `list-cases`, `run-case`, `run-suite`, and `help`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Detailed command pages SHALL contain their own numbered workflow. Case families SHALL remain reference resources owned by the top-level skill and SHALL NOT be represented as parent-scoped subskills.

#### Scenario: Agent selects one full case workflow
- **WHEN** a maintainer invokes `run-case` for one catalog case
- **THEN** the skill plans the run, snapshots context, executes the case, collects evidence, adjudicates the attempt, repeats as configured, and reports the aggregate result

#### Scenario: Agent loads only relevant case material
- **WHEN** the selected case belongs to one case family
- **THEN** the skill loads the shared contracts and that family page
- **AND THEN** it does not require every case-family page in context

### Requirement: The case catalog is committed and reviewable
The skill SHALL include a committed `references/case-catalog.md` and family pages for activation and native prompt delivery, admin routing, managed-agent routing, shared routines, loops, and generated prompts.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Every catalog case SHALL declare a stable id, revision, applicable providers, context type, required pack, native system-prompt posture when applicable, activation mode, exact stimulus, expected root and route, required observables, forbidden observables, permitted effects, evidence requirements, repetitions, timeout, and cleanup.

The skill MUST NOT generate or rewrite its case oracle dynamically from the current runtime manifest. It MAY compare the committed catalog with the manifest to report drift.

#### Scenario: Maintainer reviews the behavior suite without executing it
- **WHEN** a maintainer invokes `list-cases`
- **THEN** the response lists committed case ids, families, contexts, activation modes, and default repetitions
- **AND THEN** it performs no provider launch or runtime mutation

#### Scenario: Runtime route map changes
- **WHEN** a planning preflight detects that the current system-skill manifest and committed route-coverage cases disagree
- **THEN** the run is incomplete with a catalog-drift diagnostic
- **AND THEN** the skill does not silently regenerate expectations from the changed manifest

### Requirement: The initial catalog covers critical system-skill behavior
The activation and native-prompt family SHALL cover narrow implicit welcome activation, unrelated-task non-activation, explicit-only root non-activation, explicit root selection, native managed role-prompt delivery before the first turn, rejection of every `${identifier}` placeholder, stale projection removal, and role-prompt persistence across supported rebuild and relaunch flows.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The admin family SHALL cover help, empty invocation delegation, ordinary shared routing, target ambiguity, agent-only route rejection, welcome handoff, and actor-spoof rejection.

The managed-agent family SHALL cover help, self-route identity verification, fresh repeated verification, identity failure, admin-only route rejection, explicit peer targeting, actor-spoof rejection, and eligible self defaulting.

The shared family SHALL cover direct admin default, leading `as-agent`, inherited-frame preservation, selective child loading, specialist aliasing, wrong-actor rejection, and missing loop sibling behavior. It SHALL also provide route-matrix coverage for every current manifest route.

The loop family SHALL cover generic-request non-activation, explicit pro, explicit lite, help, inherited frame, leading `as-agent`, and direct admin default behavior.

The generated-prompt family SHALL cover notifier mail rounds, ordinary mailbox prompts, missing dependencies, admin wording in an agent pack, and managed-self wording in an admin pack.

#### Scenario: Maintainer runs the critical suite
- **WHEN** a maintainer selects the initial critical case catalog
- **THEN** every named behavior family has at least one selected case
- **AND THEN** both expected activation and expected non-activation are represented

#### Scenario: Maintainer checks complete route coverage
- **WHEN** the current manifest lists an admin or agent entrypoint route
- **THEN** the committed catalog identifies a safe behavioral probe or an explicit unsupported reason for that route

### Requirement: Every run uses isolated and frozen context
Each run SHALL use a fresh root below `tmp/houmao-dev-behavior-testing/<run-id>/` and SHALL freeze a run manifest before the first stimulus.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The context snapshot SHALL record Git revision and dirty posture, Houmao release, skill installation method, pinned `houmao-skills` source and tag when applicable, public skill version and digests, selected pack or explicit sibling set, native provider system-prompt method and digests when applicable, provider executable and version, model when observable, context type, fixture identifiers, generated prompt digest when applicable, and allowed mutation roots. It MUST NOT record credential values or hidden reasoning.

Current-checkout qualification SHALL use package-local manager installation or its supported symlink mode. Published-release qualification SHALL pin `https://github.com/igamenovoer/houmao-skills#<houmao-release-tag>` to the release under test. The unqualified repository URL SHALL be reserved for cases that explicitly qualify latest-stable discovery or default installation behavior.

Raw admin cases SHALL use an isolated skill projection and SHALL delegate provider launch to `houmao-dev-launch-agents`. Managed-agent cases SHALL use supported Houmao launch surfaces so the agent pack, native prompt projection, and self-identity authority are genuine.

#### Scenario: Behavior case prepares an admin provider context
- **WHEN** an admin-context case starts
- **THEN** the run uses a disposable workdir and isolated admin-pack projection
- **AND THEN** launch provenance identifies the selected development-launcher route without exposing secrets

#### Scenario: Behavior case prepares a managed-agent context
- **WHEN** a managed-agent case starts
- **THEN** the agent is created through a supported Houmao managed launch path
- **AND THEN** the run records agent-pack, native prompt, and verified identity authority evidence

#### Scenario: Behavior case qualifies a published release
- **WHEN** a case targets one released `houmao-mgr` version
- **THEN** the fixture installs from the matching immutable `houmao-skills` Git tag
- **AND THEN** the frozen context records the source URL, tag, installed roots, top-level versions, and content digests

### Requirement: Evidence remains observable and immutable
Each attempt SHALL preserve the exact stimulus, context snapshot, provider-native skill events when available, transcript or terminal evidence, observed commands, bounded filesystem and runtime before-and-after evidence, final response, and adjudication record.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Provider-native skill events SHALL be the strongest activation evidence. Commands, file access, state changes, and visible response semantics MAY support routing and behavior verdicts but MUST NOT be described as hidden chain-of-thought. Raw evidence SHALL remain unchanged after adjudication.

#### Scenario: Provider exposes native skill selection
- **WHEN** a provider exposes a native event naming the selected skill
- **THEN** the activation verdict uses that event and preserves it in the attempt evidence

#### Scenario: Provider hides skill selection
- **WHEN** downstream behavior is visible but no reliable native event or equivalent root-selection evidence exists
- **THEN** activation is recorded as `unobservable`
- **AND THEN** the skill does not infer a full activation pass from the final prose alone

### Requirement: Verdicts are dimensional and repeated
Each attempt SHALL record `pass`, `fail`, `incomplete`, or `unobservable` independently for activation, routing, actor, gates, effects, and outcome. A forbidden actor transition, skipped required identity check, forbidden mutation, or forbidden implicit loop activation SHALL fail the corresponding dimension regardless of final answer quality.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Unless a case declares a stronger policy, each `(case, provider)` qualification SHALL use three fresh-session attempts. Aggregate status SHALL be one of `stable-pass`, `flaky`, `stable-fail`, `inconclusive`, or `behavior-pass-activation-unobserved`.

The aggregate MUST preserve all attempt verdicts and MUST NOT use majority vote to hide an intermittent failure.

#### Scenario: All attempts satisfy every required observable dimension
- **WHEN** all required dimensions pass in all configured attempts
- **THEN** the aggregate is `stable-pass`

#### Scenario: Attempts disagree
- **WHEN** at least one attempt passes and at least one attempt fails a required dimension
- **THEN** the aggregate is `flaky`
- **AND THEN** every attempt remains linked from the report

#### Scenario: Behavior passes but activation is unobservable
- **WHEN** all observable required behavior dimensions pass and activation evidence is unavailable in every attempt
- **THEN** the aggregate is `behavior-pass-activation-unobserved`
- **AND THEN** the report states that full activation qualification was not established

### Requirement: Behavior reports are scoped and non-corrective
The final report SHALL lead with aggregate outcome and SHALL identify case and catalog revisions, provider and context versions, attempt counts, dimensional verdicts, evidence paths, catalog drift, cleanup status, and limitations.

A failed case SHALL identify a candidate system-skill defect but MUST NOT authorize or perform a change to the packaged skill under test. Runtime skill fixes SHALL be proposed and implemented separately.

#### Scenario: Live case reveals a system-skill failure
- **WHEN** a case receives `stable-fail` or `flaky`
- **THEN** the report links the evidence and names the violated semantic oracle
- **AND THEN** the behavior-testing workflow leaves packaged system-skill content unchanged
