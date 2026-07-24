# Use Case UC-01: Author and Deploy an Agent Definition With Skills From a Directory

## Actor Goal

As a human Houmao operator, I want to describe a reusable individual agent in my own terms, including a directory containing the skills that belong to it, so that an operator agent can preserve my requirements, interpret them into a strict reusable Agent Definition, and later deploy a task-targeted project profile whose active agent can discover those skills without depending on the original directory.

## Use Case

The operator authors a reusable individual agent through an Agent Definition Workspace. The authoring workflow writes all original requirements into the single freeform entrypoint `intent/src/agent-def-overview.md`, including the supplied skill path. If the source later needs supporting files, the overview references them explicitly. The workflow derives a reviewable operator-agent interpretation under `intent/derived/`, inspects and copies the requested complete Agent Skills, and prepares `materialization.toml`. After review and approval, Houmao materializes an immutable `agent-definition/` revision containing the copied skills and declared deployment bindings.

Later, the operator invokes the existing `houmao-agent-definition` deployment subcommand for one concrete task and project. The workflow validates a typed Deployment Request, resolves only definition-declared bindings, creates a deterministic Deployment Plan, and publishes the project specialist, profile, and static skill material through a recoverable apply operation. Deployment returns the profile launch command but does not launch. A separate explicit launch projects the private skills into the active provider tool home's normal skill-discovery directory.

## Supported Actions

### Record Original Agent Requirements

- context
  - Actor **has** a description of what the reusable agent is for, how it should work, and a readable local directory containing its skills.
  - System **has** the Agent Definition authoring routine and a user-selected definition workspace.
- intent
  - Actor **wants** the original definition requirements preserved in human-editable form before an operator agent translates them into Houmao contracts.
  - Actor **wonders** "If I say this agent owns the skills under `/work/reviewer-materials/skills`, where is that requirement recorded?"
- action
  - Actor then **asks** the authoring workflow to initialize the definition from the supplied requirements.
- result
  - Actor **gets** one freeform `intent/src/agent-def-overview.md` containing all supplied information, including the literal skill-directory requirement.

### Review the Operator-Agent Interpretation

- context
  - Actor **has** current source intent.
  - System **has** inspected the source requirements and explicit skill directory.
- intent
  - Actor **wants** to see how Houmao interprets the agent's purpose, specialist/profile split, mandatory skills, and task-variable fields.
  - Actor **wonders** "Did the operator agent understand which parts define the reusable reviewer and which parts should vary per task?"
- action
  - Actor then **asks** the workflow to derive or clarify the definition.
- result
  - Actor **gets** `interpretation.md`, `materialization.toml`, copied materials, validation, and approval state that identify component mappings, declared bindings, assumptions, and blockers.

### Approve and Materialize the Reusable Definition

- context
  - Actor **has** a current materialization contract and derived material.
  - System **has** validated the contract and candidate Agent Definition Revision.
- intent
  - Actor **wants** one portable immutable revision that retains only declared deployment bindings.
  - Actor **wonders** "Can I reuse this reviewer definition for several tasks without reopening the original source directory?"
- action
  - Actor then **reviews**, **approves**, and **materializes** the definition.
- result
  - Actor **gets** a validated `agent-definition/` containing `definition.toml`, `deploy-contract.toml`, `instance-contract.toml`, copied complete skills, assets, provenance, and approval evidence.

### Deploy the Definition for a Concrete Task

- context
  - Actor **has** a valid built-in or explicit local materialized Agent Definition, a selected Houmao project, and a concrete task instruction.
  - System **has** the protected `deploy-definition` subcommand and deterministic plan/apply services.
- intent
  - Actor **wants** task-specific values resolved through the definition's declared bindings without changing immutable definition meaning.
  - Actor **wonders** "Can I deploy this reviewer for the payment migration while keeping its mandatory review method and skills?"
- action
  - Actor then **invokes** `deploy-definition` with the selected definition, project, task instruction, and required project selections.
- result
  - Actor **gets** a validated Deployment Request, deterministic Deployment Plan, applied specialist/profile/skill deployment, doctor result, and exact launch command.

### Launch an Agent That Can Discover the Skills

- context
  - Actor **has** a healthy Agent Deployment and the returned profile-backed launch command.
  - System **has** copied rendered complete skills into deployment-owned project content and attached them to the concrete profile.
- intent
  - Actor **wants** the active agent to discover the definition's skills through its normal provider-specific skill mechanism.
  - Actor **wonders** "Will the agent still find its skills if `/work/reviewer-materials/skills` is moved?"
- action
  - Actor then **launches** the generated profile in a separate explicit operation.
- result
  - Actor **gets** an active managed agent whose constructed tool home contains the deployment-owned skill copies, independent of the original authoring path.

## Main Flow

1. The human selects an Agent Definition Workspace and asks `houmao-admin-entrypoint` to define a reusable reviewer agent.
2. The user says that the agent is for repository review, describes how it performs review, and states that its skills are under `/work/reviewer-materials/skills`.
3. The admin entrypoint selects the protected Agent Definition authoring route.
4. `init-intent` creates only `intent/src/agent-def-overview.md` and records all original requirements, paths, assumptions, and open questions in that file.
5. `derive-intent` reads the overview and any confined supporting files that it explicitly references, without rewriting source or scanning unreferenced siblings.
6. Derivation maps the reusable agent to specialist, project-profile, prompt-overlay, memo-seed, and skill surfaces.
7. Derivation inspects immediate non-hidden child directories beneath the explicit skill root in stable order.
8. Each child containing `SKILL.md` is validated as a complete Agent Skill. Non-skill entries are reported; malformed candidates block derivation.
9. Accepted skills are copied into `intent/derived/materials/skills/`, and source and per-skill digests are recorded in `validation.json`.
10. Derivation identifies fixed purpose and method plus typed deployment inputs and bindings such as `task_objective` and `done_when`.
11. Derivation writes `interpretation.md`, `materialization.toml`, candidate material, and validation.
12. The human reviews the derived interpretation. `clarify-intent` integrates accepted corrections into the owned source and derived surfaces.
13. `draft-definition` previews the immutable revision and generic validation results.
14. The human approves the derived result or explicitly authorizes authoring fast-forward. Approval provenance records the derived digest, review summary, actor/session, mode, and validation reference.
15. `materialize-definition` invokes the maintained `materialization.toml`-backed materializer.
16. Houmao writes `agent-definition/` with `definition.toml`, `deploy-contract.toml`, `instance-contract.toml`, assets, complete copied skills, provenance, and validation.
17. The original skill source path is no longer required by the materialized definition.
18. Later, the human selects a Houmao project and invokes `deploy-definition` for reviewing the payment migration.
19. The deployment routine validates and snapshots the materialized definition.
20. It preserves the exact deployment instruction, collects and confirms definition-declared deployment arguments, and writes a Deployment Request bound to the definition digest.
21. If the user requests a change outside declared bindings, the routine stops and directs the user to revise and rematerialize the definition.
22. The deterministic planner consumes only the revision snapshot and Deployment Request, resolves declared bindings, rejects unresolved markers, validates final skills and project fields, and writes a digest-protected Deployment Plan.
23. After authorization, apply stages deployment-owned content, commits one catalog-visible Agent Deployment after every artifact is ready, and journals recoverable publication state.
24. Deployment doctor verifies catalog relationships, operation state, output digests, generated skills, definition provenance, and launch readiness.
25. The Agent Definition routine reports the exact `houmao-mgr project agents launch --profile <profile>` command and stops.
26. In a separate explicit operation, the operator launches the profile.
27. Managed launch copies profile-private skills into the provider's normal skill-discovery directory.
28. The active agent can discover and invoke the skills by installed name without reading authoring intent or the original source directory.

## Alternative and Exception Flows

- If the user does not supply a definition workspace, authoring asks for it and creates no files.
- If `agent-def-overview.md` is missing outside initialization, derivation stops rather than treating sibling files or chat context as source.
- If the overview references a missing, escaping, symlinked, or non-regular supporting file, source validation blocks derivation.
- If `intent/src/` contains an unreferenced sibling, derivation reports and ignores it.
- If source intent is vague, derivation preserves known facts and records focused open questions instead of inventing policy.
- If source intent changes after derivation, freshness validation marks `intent/derived/` stale and blocks authoritative materialization.
- If the skill source path is missing, unreadable, or not a directory, derivation reports the exact authoring-time blocker.
- If a child has no `SKILL.md`, derivation reports it as ignored and does not recurse into it.
- If a child has malformed `SKILL.md`, a symlink, special file, unsafe name, package-limit violation, or reserved-name collision, derivation blocks rather than silently omitting it.
- If the original skill path changes after materialization, the existing revision remains stable because it owns copied skill content. Provenance inspection may report source drift when the old source remains resolvable.
- If an authoring question affects the agent's core purpose or safety posture, materialization blocks rather than converting the unknown into a deployment placeholder.
- If derived material is valid but unapproved, materialization may preview but does not write the authoritative revision.
- If deployment omits a required task placeholder, the deployment routine asks a focused question and does not plan.
- If a deployment instruction requests an edit to an immutable surface, deployment blocks and recommends re-authoring or forking the definition.
- If a requested change has no declared deployment binding, deployment blocks and requires a new revision.
- If a rendered skill or prompt retains an unresolved deployment placeholder, planning blocks before project mutation.
- If target specialist, profile, skill, or deployment names collide, planning blocks without inferring replacement.
- If apply stops after staging content, doctor uses the operation journal to complete publication or remove only operation-owned staging. No incomplete deployment is reported as healthy.
- If the operator asks only to author or materialize, no project deployment occurs.
- If the operator asks only to deploy or prepare, the workflow does not launch a live agent.

## Durable Outputs

- Human-owned original requirements in `intent/src/agent-def-overview.md` and any supporting source files explicitly referenced from it.
- Operator-derived `interpretation.md`, `materialization.toml`, copied source skills, validation, and approval under `intent/derived/`.
- A portable immutable Agent Definition Revision with typed deployment bindings, an instance-contract boundary, complete copied skills, provenance, and validation.
- A definition snapshot, Deployment Request, deterministic Deployment Plan, rendered output, and validation.
- Deployment-owned specialist, profile, prompt, memo, registered skill, and private skill content.
- Catalog ownership and last-applied digests for the Agent Deployment.
- Doctor evidence distinguishing definition source drift, output drift, policy/provenance errors, and broken state.
- An exact profile-backed launch command, with no live agent created by authoring, materialization, or deployment.
- On later launch, a managed tool home containing each selected skill in the provider's normal discovery destination.

## Example Prompt and Expected AI Responses

### Event 001: Author the Reusable Definition

> Time: `design example` · Session: `human operator authoring a reusable definition`

User Prompt:

> `$houmao-admin-entrypoint define a repository-reviewer agent under ./agent-definitions/repository-reviewer. It performs evidence-backed repository reviews and must report findings by severity. This agent has the skills under /work/reviewer-materials/skills, and it must be able to find them when active. Task objective and completion criteria vary per deployment.`

Expected AI:

> The assistant creates or updates only `intent/src/agent-def-overview.md`, preserving all supplied purpose, method, skill path, and task variability in that freeform file. It derives the Houmao component mapping, inspects and copies valid source skills, proposes typed deployment inputs and bindings for task objective and completion criteria, and presents `interpretation.md` plus `materialization.toml` for review. It does not create topic-specific source forms, a project specialist, or a live agent.

### Event 002: Deploy for One Task

User Prompt:

> `$houmao-admin-entrypoint deploy the materialized repository-reviewer definition into the current project for reviewing the payment migration. Focus on data-loss and rollback risks, and finish when every changed migration path has evidence-backed findings or an explicit no-finding result. Use Codex and reviewer-creds.`

Expected AI:

> The assistant routes to the existing Agent Definition routine, validates the materialized revision, binds the task objective and completion criteria, and resolves current-project settings. It accepts the data-loss emphasis only when a declared deployment input targets that guidance; otherwise it requests a revised definition. It previews the Deployment Request and deterministic Plan, applies the recoverable operation, runs doctor, and prints `houmao-mgr project agents launch --profile <generated-profile>`. It does not launch.

## Assumptions and Open Questions

- Source skill directories are authoring-time inputs by default. Their accepted skills are copied into the reusable Agent Definition Revision.
- A definition may explicitly declare a per-deployment `skill-selection` placeholder when its design genuinely requires task-selected skills, but this is not inferred from an authoring source path.
- Collection discovery is shallow and deterministic.
- Materialized revisions may contain declared deployment markers; concrete project specialists, profiles, and installed skills may not.
- V1 deployment changes only declared typed bindings. Other content changes require a new Agent Definition Revision.
- Definition deployment and live managed-agent launch remain separate.
- No v1 feature fetches definitions or skills from the network.

## Relationship to Existing Work

- Houmao's current specialist/profile commands remain the concrete project-object implementation.
- Existing profile-private skill projection remains the launch-time discovery mechanism.
- The agent-loop source/generated/preparation boundary informs the lifecycle, while the adopted `intent/src` and `intent/derived` layout follows Isomer Labs.
- The surrounding OpenSpec change retains deployment ownership, recoverable apply, doctor, update, removal, and no-runtime-composition requirements, but moves user skill paths and reusable meaning into authoring and materialization.
