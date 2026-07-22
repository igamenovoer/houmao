# houmao-system-skill-semantic-preservation Specification

## Purpose
TBD - created by archiving change replace-runtime-skill-composition-with-static-collection. Update Purpose after archive.
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

Any additional intentional semantic change SHALL be recorded explicitly with its source evidence, target behavior, and rationale. Formatting alone SHALL NOT broaden triggers, rename public operations or aliases, change output paths, remove gates, weaken blockers, alter side effects, or remove stop conditions.

#### Scenario: Formatting moves an action page to commands
- **WHEN** a source procedure moves from `actions/` or a procedure-only legacy `subskills/` directory into `commands/`
- **THEN** its invocation meaning, required inputs, output contract, and guardrails remain equivalent
- **AND THEN** every link and route is updated to the new owned path

### Requirement: Original sources map to the fixed target owners
The sixteen ordinary source skills SHALL map to the sixteen children of `houmao-shared-routines`. `houmao-agent-loop-pro` and `houmao-agent-loop-lite` SHALL map to top-level standalone skills. `houmao-touring` SHALL map to `houmao-admin-welcome`. `houmao-specialist-mgr` SHALL map to an admin/shared compatibility alias that delegates to agent-definition.

The specialist alias SHALL preserve the original wrapper's read-only explanation and no-independent-command ownership. It SHALL NOT become a separate top-level root or an independent shared child.

#### Scenario: Old specialist route is requested
- **WHEN** an admin or direct-shared caller uses the `specialist-mgr` compatibility route
- **THEN** the route identifies agent-definition as canonical
- **AND THEN** it delegates the supported task without implementing separate specialist commands

### Requirement: Every runtime instruction page follows current Imsight format
Every standalone `SKILL.md`, parent-scoped `SKILL-MAIN.md`, and executable subcommand page SHALL contain a concise numbered `## Workflow` near the top. The workflow SHALL reference detailed sections for complex logic and SHALL end with the native-planning fallback for tasks that do not map cleanly.

Each skill SHALL use the collection-of-routines or complex-procedure subcommand flavor that matches its behavior. Pro and lite loops SHALL use the complex-procedure flavor; peer routine routers SHALL use the collection flavor.

#### Scenario: Validator inspects a migrated command page
- **WHEN** a Markdown page can be selected as an executable operation
- **THEN** it has a numbered workflow and freeform fallback
- **AND THEN** its detailed domain procedure remains outside long workflow lines

### Requirement: Imsight role and notation rules are enforced
Standalone roots SHALL use `SKILL.md`; shared children SHALL use `SKILL-MAIN.md`; and no runtime directory SHALL contain both. Pages using object-style designators SHALL declare the standard `skill_invocation_notation` frontmatter value.

Skill and subskill entrypoints SHALL use bare object components, every subcommand component SHALL use parentheses, and command chains SHALL NOT return to a bare component after a subcommand begins.

#### Scenario: Route notation is validated
- **WHEN** an entrypoint documents delegation from its route subcommand to a shared child command
- **THEN** the entrypoint route is parenthesized as a subcommand
- **AND THEN** the shared child is a bare subskill component followed by a parenthesized child command

### Requirement: Imsight routing descriptions and guardrails remain semantic
Every direct shared child row SHALL contain one `When to Route Here` sentence that distinguishes it from siblings and is not copied verbatim from child metadata. Every skill entrypoint SHALL have a concise `## Guardrails` section whose bullets begin `DO NOT` and contain only negative-action prevention.

Positive requirements SHALL remain in workflows, contracts, or procedures. Rewriting a source prohibition into Imsight guardrail form SHALL preserve its force and scope.

#### Scenario: Original guardrail is normalized
- **WHEN** a source entrypoint contains a domain-specific `Do not` rule
- **THEN** the target retains the prohibition as a `DO NOT` guardrail or an equally strong owning-page constraint
- **AND THEN** it does not silently turn the prohibition into optional advice

### Requirement: Discovery metadata preserves activation meaning
Frontmatter descriptions SHALL start with `Use when...`, describe trigger conditions, and retain the original manual, explicit, or narrow implicit activation boundary. `agents/openai.yaml` SHALL agree with that boundary.

Welcome MAY allow narrow implicit orientation. Actor entrypoints, shared routines, and both loops SHALL disable implicit invocation. Manual-only source behavior SHALL NOT become generic automatic routing because the skill is now public.

#### Scenario: Host discovers the pro loop skill
- **WHEN** a host loads pro-loop metadata
- **THEN** the metadata allows explicit manual invocation
- **AND THEN** it does not implicitly route a generic loop request to pro

### Requirement: Semantic preservation has executable verification
Tests SHALL use a checked-in preservation inventory derived from the Git baseline and SHALL assert operations, aliases, default behavior, read-only help, critical gates, actor boundaries, outputs, and stop conditions for every migrated source.

The test suite SHALL NOT require Git history at runtime. Byte equality SHALL be used for static installation, while behavior-preservation assertions SHALL be used for reformatted skill content.

#### Scenario: Skill prose changes without operation loss
- **WHEN** an Imsight formatting edit changes wording or file layout
- **THEN** semantic-preservation tests continue to validate the source-derived operation and gate inventory
- **AND THEN** byte-identity tests apply only between the final static source and installed copy

