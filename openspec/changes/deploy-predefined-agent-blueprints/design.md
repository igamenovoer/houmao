## Context

Houmao already models a reusable project agent as a specialist plus an optional specialist-backed project profile. A specialist owns reusable role, tool, credential, launch, and registered-skill choices. A profile adds birth-time identity, workdir, prompt overlays, private skills, memo seed, mailbox, gateway, and launch overrides. The existing `houmao-agent-definition` protected routine can create those objects, but the operator or driving agent must decide and author every component independently.

The agent-loop authoring flow has a related two-stage pattern: an authoring agent records intended bindings, and a later preparation step creates concrete project definitions. The new feature generalizes that separation for one individual agent without coupling individual-agent creation to an ExecPlan or changing managed-agent launch.

The design must satisfy two distinct needs:

- A blueprint author must be able to express a stable agent purpose and operating method as a portable directory.
- A human operator must be able to describe a task informally and have an admin assistant adapt only the blueprint's declared task fields before Houmao installs a concrete, inspectable definition.

Blueprint content is untrusted local input. It must not become a code-execution surface, a secret store, or an indirect way to mutate paths outside the selected project overlay. Generated skills must exist as complete static directories before launch; managed-agent startup must not compose or rewrite them.

## Goals / Non-Goals

**Goals:**

- Define a versioned, portable package for one individual-agent archetype.
- Support built-in blueprints shipped with Houmao and explicit local blueprint directories.
- Separate fixed agent behavior from typed task-specific inputs.
- Let an LLM interpret informal task context while keeping rendering and project mutation deterministic.
- Materialize one deployment into a specialist, a profile, complete skill directories, optional prompt overlay, and optional memo seed.
- Preview names, files, resource changes, and collisions before durable definition mutation.
- Record ownership and provenance so Houmao can inspect, diagnose, update, and remove a deployment safely.
- Route the workflow through the human-operator entrypoint and existing protected agent-definition routine.
- Return a normal `houmao-mgr project agents launch --profile ...` command without launching an agent.

**Non-Goals:**

- Fetching blueprints from network repositories or defining a blueprint marketplace.
- Executing blueprint-provided scripts, hooks, expressions, or arbitrary template code.
- Launching a managed agent as part of deployment.
- Defining multi-agent teams, dependency graphs, or loop execution plans.
- Dynamically composing skills during managed-agent launch.
- Merging operator edits into regenerated files.
- Sharing one deployment-owned specialist or generated skill across unrelated deployments.
- Preserving or recognizing the retired native-agent `blueprints/` directory format.

## Decisions

### Use an Agent Blueprint and Agent Deployment as Separate Concepts

An **agent blueprint** is a portable authoring package. It declares fixed behavior, supported tools, typed input fields, output templates, and skill sources. An **agent deployment** is a project-local materialization of one blueprint and one normalized input set.

The deployment owns one specialist and one specialist-backed profile. It can also own project-registered skills and profile-private skills. A live managed agent remains a separate runtime object launched later from the generated profile.

This terminology avoids treating the source package as a specialist template. A blueprint spans specialist, profile, skill, and memo concerns, while a specialist remains one existing Houmao project object.

Alternative considered: extend specialist creation with a template directory. That would hide profile and private-skill ownership under a specialist-only name and would make provenance and removal ambiguous.

### Combine Semantic Input Synthesis with a Deterministic Compiler

The system skill will translate the user's informal task into a normalized JSON input document whose fields are declared by the selected blueprint. `houmao-mgr` will then validate the blueprint and input document, render strict placeholders, stage the outputs, detect collisions, and apply an authorized plan.

The LLM may synthesize values such as the objective, scope, expected deliverables, and completion criteria. It may not add undeclared fields that control output paths, object names, credentials, CLI flags, or mutation policy.

Alternative considered: let the skill issue a sequence of existing specialist, skill, and profile commands. That approach is quick, but it allows partial creation, loses a single provenance boundary, and cannot diagnose deployment-level drift.

Alternative considered: use deterministic templating without semantic synthesis. That is safe but does not satisfy the requirement to adapt an informal user task into blueprint-specific material.

### Define a Strict Versioned Blueprint Manifest

Each blueprint directory will contain `blueprint.toml` and may contain the following package-owned directories:

```text
<blueprint>/
├── blueprint.toml
├── README.md
├── templates/
│   ├── specialist-prompt.md
│   ├── profile-overlay.md
│   └── memo-seed.md
├── skills/
│   └── <logical-skill>/
│       ├── SKILL.md
│       ├── commands/
│       ├── references/
│       └── assets/
└── references/
```

The v1 manifest uses `schema_version = "houmao-agent-blueprint.v1"` and declares:

- a stable blueprint id and blueprint version;
- a human-readable purpose;
- supported Houmao tool families;
- typed input declarations with required state and authoring guidance;
- optional specialist prompt, profile overlay, and memo-seed template paths;
- zero or more skill directories, output names, and either `profile_private` or `project_registered` binding;
- fixed profile and launch-policy defaults that the schema explicitly permits.

V1 input types are `string`, `markdown`, `string-list`, and `boolean`. The normalized input document uses JSON values matching those types. Runtime selections such as tool, credential, workdir, model, reasoning level, mailbox, and headless posture remain deployment command inputs rather than free-form template fields.

The initial built-in catalog will include a small `repository-reviewer` blueprint that exercises specialist prompt, profile overlay, memo, and private-skill rendering. Built-ins live in a package-data tree dedicated to agent blueprints, separate from the system-skill and starter native-agent trees.

Alternative considered: use the existing config-draft format as the package manifest. Config drafts describe one maintained CLI configuration shape and do not describe a portable multi-output source package.

### Use a Non-Executable Placeholder Language

Text files declared as templates and text files under declared skill directories may contain placeholders with the form:

```text
{{houmao.input.task.objective}}
{{houmao.input.task.done_when}}
```

The renderer performs exact field lookup and type-aware deterministic formatting. A `string-list` renders as a Markdown list when inserted into Markdown or skill text. The v1 language has no conditions, loops, includes, filters, attribute access, environment expansion, shell expansion, or expression evaluation.

Validation fails for unknown placeholders, missing required inputs, type mismatches, placeholders in undeclared binary files, or unresolved placeholder markers after rendering. Blueprint authors express optional behavior through separate optional output declarations and explicit manifest defaults, not template control flow.

Alternative considered: Jinja. Its flexibility would make packages harder to audit and would introduce expression, loader, and escaping behavior that the feature does not need.

### Treat Blueprint Packages as Untrusted Data

Blueprint validation will:

- reject absolute package member paths, `..` traversal, symlinks, device files, sockets, and other non-regular package members;
- allow reads only beneath the lexical blueprint root;
- allow only manifest-declared template and skill paths;
- reject secrets and credential material in declared inputs by contract and keep credential selection outside the rendered input document;
- validate generated skill directory names, `SKILL.md` presence and frontmatter, reserved Houmao skill names, duplicate names, and size/count limits;
- derive target names from a sanitized deployment name rather than task prose;
- stage a snapshot and digest before rendering so local source changes cannot alter an existing plan;
- never execute a blueprint member.

Built-in assets go through the same validator as local directories.

### Add Blueprint Discovery and Deployment Command Groups

The project CLI will add:

```text
houmao-mgr project agent-blueprints list
houmao-mgr project agent-blueprints inspect --blueprint <builtin:id-or-local-path>

houmao-mgr project agent-deployments plan ...
houmao-mgr project agent-deployments apply --plan <plan-id>
houmao-mgr project agent-deployments list
houmao-mgr project agent-deployments get --name <deployment>
houmao-mgr project agent-deployments doctor --name <deployment>
houmao-mgr project agent-deployments remove --name <deployment>
```

`agent-blueprints list` lists built-ins because arbitrary local paths are not registered globally. `inspect` accepts `builtin:<id>` or an explicit local directory, validates it, and reports its manifest, required inputs, supported tools, outputs, and digest.

`agent-deployments plan` accepts a blueprint reference, deployment name, normalized inputs file, tool, credential display name, workdir, and maintained optional profile settings. It ensures the selected project overlay exists, but makes no specialist, profile, skill-registration, or deployment-record mutation. It writes an opaque plan under:

```text
.houmao/jobs/agent-deployments/<plan-id>/
├── plan.json
├── source/
└── rendered/
```

The plan records the selected overlay identity, blueprint and input digests, resolved target names, expected preconditions, rendered output digests, and planned catalog/content mutations. Structured and plain output show collisions, warnings, and the plan id.

`apply` accepts only a plan under the selected overlay's jobs root. It revalidates the plan schema, overlay identity, source and rendered digests, credential identity, target preconditions, and current catalog schema. It then applies the complete deployment through one internal deployment service.

Alternative considered: accept a plan file at any path. Restricting plans to the selected overlay's jobs root prevents applying a plan constructed for another project and narrows mutation inputs.

### Make Apply Observably Atomic

The deployment service will preflight every catalog relationship and filesystem destination before mutation. It will prepare replacement trees under overlay-owned temporary paths, perform catalog writes through one SQLite transaction, use atomic path replacement for managed content, and remove temporary paths on failure.

Because SQLite and filesystem renames do not share one transaction manager, the service will keep rollback copies until the database commit and projection materialization succeed. If an exception occurs before completion, it restores replaced lexical artifacts and rolls back the database connection. The command reports success only after the catalog, managed content, and compatibility projection agree.

The deployment layer will call reusable specialist/profile/catalog primitives through transaction-aware internal APIs. It will not invoke Click commands recursively.

Alternative considered: create each object with the existing public command handlers. Those handlers own separate transactions and would expose partial deployments after a later failure.

### Persist Deployment Provenance in the Project Catalog

The catalog schema will add a canonical deployment table and stable read view. Each record stores:

- deployment id and unique operator-facing name;
- blueprint id, version, source kind, source reference, and source digest;
- normalized-input content reference and digest;
- owned specialist id and launch-profile id;
- an output manifest containing owned registered-skill identities, private-skill paths, managed content references, and last-applied digests;
- creation and last-application timestamps.

Normalized inputs are stored once as managed file-backed content under the deployment root. Generated specialist prompts, profile overlays, memo content, registered skills, and private skills use their normal managed content locations or deployment-owned private-skill subtree. The catalog stores semantic ownership and content references instead of relying on directory nesting.

Deployment-owned private skills are complete static skill directories beneath:

```text
.houmao/content/agent-deployments/<deployment-id>/skills/<skill-name>/
```

They are attached to the generated profile through existing private-skill semantics. Deployment-owned registered skills use unique deployment-derived names under the canonical project skill root and are attached through existing registered-skill relationships.

The catalog schema version will be incremented. Existing overlays will use the explicit `houmao-mgr project migrate` workflow for the known prior schema rather than receiving an implicit upgrade during ordinary catalog access.

Alternative considered: write a deployment receipt beside the rendered files. A separate receipt would duplicate catalog relationships and would make SQL inspection, referential integrity, and safe removal weaker.

### Use Explicit Ownership and Drift Rules

Creation fails when any resolved specialist, profile, registered-skill, or deployment name already exists. There is no implicit replacement.

An update begins with `agent-deployments plan --update <deployment-name>`. Planning verifies that the selected blueprint id still matches the deployment and records every last-applied digest. Applying the update fails if an owned catalog object is missing, an owned managed file differs from the last-applied digest, or another object now references a resource that the update would replace or remove. Houmao does not merge local edits.

`doctor` compares catalog relationships, managed files, generated skill validity, current digests, blueprint provenance, and profile references. It distinguishes:

- healthy;
- source drift, where a currently resolvable local or built-in blueprint differs from the applied digest;
- output drift, where installed content or catalog objects differ from the last-applied deployment;
- broken, where required resources or relationships are missing.

`remove` refuses while a live managed agent or an unrelated catalog object references deployment-owned resources. Otherwise it removes only deployment-owned objects and lexical managed paths, then removes the deployment record. It never follows symlinks while deleting.

### Keep Deployment Separate from Launch

A successful apply and doctor pass return:

- deployment name and blueprint provenance;
- generated specialist, profile, and skill names;
- managed content locations;
- warnings, if any;
- the exact maintained `houmao-mgr project agents launch --profile <profile>` command.

The deployment command and system skill stop at that point. They do not invoke the launch command. Existing managed-agent launch continues to consume the stored profile and complete static skills without knowing that a blueprint created them.

### Extend the Existing Protected Agent-Definition Routine

`houmao-agent-definition` will add a lane-specific `deploy-blueprint` subcommand document. Its phases are:

1. Verify the admin actor frame and selected project.
2. Resolve an explicit built-in id or local blueprint directory; use read-only list and inspect when selection is ambiguous.
3. Read the declared input schema and recover explicit values from the current prompt and recent unambiguous context.
4. Ask only for required fields or runtime selections that remain unknown.
5. Synthesize the normalized inputs file while preserving the blueprint's fixed instructions.
6. Run `agent-deployments plan` and present the resolved names, output summary, collisions, and warnings.
7. Apply only when the user's request authorizes creation and the plan has no blockers. Require a new explicit update request for existing deployments.
8. Run `doctor`, report the installed definition and provenance, and print the launch command without executing it.

`houmao-admin-entrypoint` will recognize natural-language requests to deploy, instantiate, or prepare an agent from a predefined or local blueprint and route them implicitly to this admin-only routine. `houmao-shared-routines` will list the route for explicit advanced invocation. `houmao-agent-entrypoint` will not include the admin-only routine and must not mutate definitions on behalf of a managed agent.

No new top-level public skill is added.

### Document the New Term Without Reviving the Retired Layout

Documentation will define **agent blueprint** only as the new portable package described here. It will continue to reject the retired native-agent `blueprints/` tree and old brains/config-profile terminology. Blueprint authoring docs will use the new package manifest and project deployment commands, not the retired directory layout.

## Risks / Trade-offs

- [LLM synthesis changes task meaning] → Restrict synthesis to declared typed fields, preview normalized inputs and rendered output summaries, and keep fixed blueprint text outside LLM control.
- [A malicious local blueprint targets files outside the project] → Reject symlinks, traversal, special files, undeclared members, unsafe names, and plans outside the selected overlay jobs root.
- [Filesystem and SQLite changes diverge during apply] → Preflight all targets, stage content, use one catalog transaction, retain rollback copies, and report success only after compatibility projection succeeds.
- [Generated names collide with operator resources] → Derive deterministic deployment-prefixed names and fail planning before mutation.
- [An operator edits generated content] → Record last-applied digests, report output drift, and block update or removal that would overwrite or strand edits.
- [Blueprint terminology is confused with the retired native layout] → Use `agent blueprint` consistently, document its manifest, and keep the old `blueprints/` paths explicitly retired.
- [The strict template language limits sophisticated packages] → Keep v1 auditable and add declarative schema features only when concrete blueprints demonstrate a need.
- [Deployment records increase catalog schema churn] → Add one explicit migration step from the immediately preceding supported schema and keep ordinary catalog initialization non-migrating.

## Migration Plan

1. Add the blueprint package models, validator, renderer, built-in asset loader, and initial built-in blueprint without exposing mutation commands.
2. Add the catalog schema, explicit migration step, deployment repository methods, and managed deployment content root.
3. Add plan/apply service logic and project CLI groups behind unit and integration tests.
4. Add inspect, doctor, update, and removal behavior.
5. Update the protected system-skill route, admin entrypoint routing, behavior-testing cases, and documentation.
6. Release the feature with the Houmao package. Existing projects on the immediately previous catalog schema must run `houmao-mgr project migrate` before blueprint deployment or other current catalog mutation.

Rollback removes the new CLI and skill routes while leaving ordinary specialist/profile launch unaffected. A project that already contains deployment records must be restored from its pre-migration catalog backup before running an older Houmao version; older versions will reject the newer catalog schema rather than silently ignoring deployment ownership.

## Open Questions

None block v1. Additional built-in blueprints, network distribution, richer declarative formatting, and multi-agent packages require separate changes after the single-agent contract has usage evidence.
