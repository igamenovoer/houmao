# houmao-system-skill-semantic-preservation Specification

## Purpose
Preserve the operations, defaults, and guardrails of prior system skills as their instructions move into a static collection. Use the recorded Git baseline and executable checks to verify behavior and activation.
## Requirements
### Requirement: Pre-compaction Git tree is the semantic baseline
The implementation SHALL use Git commit `8f377c468bc7f87ff40dbf40c0a68327616112bd` as the authoritative pre-compaction source for the twenty original current system skills.

Before rewriting a target, the implementation SHALL inventory the source entrypoint and executable support pages for triggers, public operations and aliases, inputs, outputs, gates, blockers, evidence handoffs, side effects, target rules, help behavior, and stop conditions.

#### Scenario: Maintainer migrates one ordinary routine
- **WHEN** a maintainer rewrites an original flat skill as a shared child
- **THEN** the review evidence maps every source operation and semantic boundary to the target
- **AND THEN** unexplained omissions fail semantic-preservation validation

### Requirement: Structural migration preserves operational meaning
The migration SHALL preserve each original skill's domain behavior. Permitted changes are limited to static ownership paths, standalone versus parent-scoped entrypoint roles, actor-frame intake, actor eligibility, sibling-qualified routing, and Imsight structural normalization.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Any additional intentional semantic change SHALL be recorded explicitly with its source evidence, target behavior, and rationale. Formatting alone SHALL NOT broaden triggers, rename public operations or aliases, change output paths, remove gates, weaken blockers, alter side effects, or remove stop conditions.

#### Scenario: Formatting moves an action page to commands
- **WHEN** a source procedure moves from `actions/` or a procedure-only legacy `subskills/` directory into `commands/`
- **THEN** its invocation meaning, required inputs, output contract, and guardrails remain equivalent
- **AND THEN** every link and route is updated to the new owned path

### Requirement: Original sources map to the fixed target owners
The sixteen ordinary source skills SHALL retain their mapped ownership under `houmao-shared-routines` when the manifest adds current routines. `houmao-agent-loop-pro` and `houmao-agent-loop-lite` SHALL map to top-level standalone skills. `houmao-touring` SHALL map to `houmao-admin-welcome`. `houmao-specialist-mgr` SHALL map to an admin/shared alias that delegates to agent-definition.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The specialist alias SHALL preserve the original wrapper's read-only explanation and no-independent-command ownership. It SHALL NOT become a separate top-level root or an independent shared child.

#### Scenario: Old specialist route is requested
- **WHEN** an admin or direct-shared caller uses the `specialist-mgr` compatibility route
- **THEN** the route identifies agent-definition as canonical
- **AND THEN** it delegates the supported task without implementing separate specialist commands

### Requirement: Every runtime instruction page follows current Imsight format
Every standalone `SKILL.md`, parent-scoped `SKILL-MAIN.md`, and executable subcommand page SHALL contain a concise numbered `## Workflow` near the top. The workflow SHALL reference detailed sections for complex logic and SHALL end with the native-planning fallback for tasks that do not map cleanly.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Each skill SHALL use the collection-of-routines or complex-procedure subcommand flavor that matches its behavior. Pro and lite loops SHALL use the complex-procedure flavor. Peer routine routers SHALL use the collection flavor.

#### Scenario: Validator inspects a migrated command page
- **WHEN** a Markdown page can be selected as an executable operation
- **THEN** review checks its numbered workflow and freeform fallback
- **AND THEN** review checks that the detailed procedure lives outside long workflow lines

### Requirement: Imsight role and notation rules are enforced
Standalone roots SHALL use `SKILL.md` and shared children SHALL use `SKILL-MAIN.md`. A runtime directory SHALL contain only its role-canonical entrypoint. Each entrypoint and each instruction page with object-style designators SHALL declare `metadata.skill_invocation_notation`. Skill path components SHALL be bare. All components in a command chain SHALL use parentheses and resolve to declared operations.

#### Scenario: Route notation is validated
- **WHEN** an entrypoint documents delegation from its route subcommand to a shared child command
- **THEN** the entrypoint route is parenthesized as a subcommand
- **AND THEN** the shared child is a bare subskill component followed by a parenthesized child command
- **AND THEN** the page declares the standard notation under YAML `metadata`

### Requirement: Imsight routing descriptions and guardrails remain semantic
Each direct shared child SHALL have a distinct `When to Route Here` sentence that preserves the precise trigger boundary. Each entrypoint SHALL have a concise `## Guardrails` section. Guardrail bullets SHALL begin with `DO NOT` and express prohibitions. Positive actions SHALL appear in the owning workflow, contract, or procedure.

#### Scenario: Original guardrail is normalized
- **WHEN** a source entrypoint contains a domain-specific `Do not` rule
- **THEN** the target retains the prohibition as a `DO NOT` guardrail or an equally strong owning-page constraint
- **AND THEN** it preserves the force and scope of that prohibition

#### Scenario: Positive action appears among guardrails
- **WHEN** an entrypoint or command page requires the operator to perform a positive action
- **THEN** the owning workflow, contract, or procedure describes that action

### Requirement: Discovery metadata preserves activation meaning
Frontmatter descriptions SHALL start with `Use when` and describe trigger conditions. `agents/openai.yaml` SHALL agree with the manifest. Admin and agent entrypoints SHALL permit implicit selection in their respective actor contexts. Welcome, shared routines, and both loop roots SHALL retain manual initial selection.

#### Scenario: Host discovers the pro loop skill
- **WHEN** a host loads pro-loop metadata
- **THEN** the metadata allows explicit manual invocation
- **AND THEN** it does not implicitly route a generic loop request to pro

#### Scenario: Host selects an actor entrypoint
- **WHEN** the host handles a Houmao-related request in a genuine managed-agent context
- **THEN** the managed-agent entrypoint is eligible for implicit initial selection
- **AND THEN** it applies the configured posture and route eligibility

### Requirement: Editorial review verifies skill instruction semantics
Maintainers SHALL review changed instructions against the supported operations, triggers, guardrails, and output contracts. Unit tests of skill assets SHALL verify file existence and expected layout. Installer tests SHALL continue to verify that a static copy is byte-identical to its packaged source.

#### Scenario: Skill prose changes without operation loss
- **WHEN** an Imsight formatting edit changes wording or file layout
- **THEN** editorial review verifies preservation of operations, aliases, default behavior, read-only help, critical gates, actor boundaries, outputs, and stop conditions
- **AND THEN** asset unit tests verify file structure without a prose fixture or Git history
- **AND THEN** copy verification compares the final source and installed bytes as opaque data
