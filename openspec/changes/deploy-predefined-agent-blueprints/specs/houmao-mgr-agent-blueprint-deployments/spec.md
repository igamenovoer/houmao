## ADDED Requirements

### Requirement: Project CLI exposes blueprint discovery and inspection

`houmao-mgr project agent-blueprints list` SHALL list packaged built-in blueprints.

`houmao-mgr project agent-blueprints inspect --blueprint <source>` SHALL accept an exact `builtin:<id>` designator or explicit local directory. It SHALL validate the source and report its id, version, purpose, supported tools, declared inputs, declared outputs, and source digest without creating a specialist, profile, skill registration, or deployment record.

#### Scenario: Operator inspects a local blueprint

- **WHEN** an operator runs `agent-blueprints inspect` with a valid local blueprint directory
- **THEN** the command reports the validated manifest and source digest
- **AND THEN** the project catalog remains unchanged

### Requirement: Deployment planning stages a non-applied project plan

`houmao-mgr project agent-deployments plan` SHALL accept:

- a blueprint source;
- a unique deployment name;
- a normalized inputs file;
- a supported tool;
- an existing credential display name;
- a workdir;
- maintained optional project-profile settings.

The command SHALL ensure that the selected project overlay exists and SHALL stage one opaque plan under `.houmao/jobs/agent-deployments/<plan-id>/`. Planning MAY create overlay and job artifacts, but SHALL NOT create or update a specialist, profile, project skill registration, deployment record, or live agent.

The plan SHALL record the selected overlay identity, blueprint snapshot and digest, normalized-input digest, rendered outputs and digests, resolved target names, expected catalog preconditions, and planned mutations.

#### Scenario: New deployment plan has no definition side effects

- **WHEN** an operator creates a valid plan for deployment `payments-reviewer`
- **THEN** the command returns a plan id and stages source and rendered artifacts beneath the selected overlay jobs root
- **AND THEN** no specialist, profile, project skill registration, deployment record, or live managed agent named for that deployment exists yet

### Requirement: Planning detects blockers before mutation

Planning SHALL validate the blueprint, normalized inputs, tool compatibility, credential identity, generated skill packages, target names, output paths, and current catalog state.

Creation planning SHALL fail closed when the deployment name, specialist name, profile name, or generated registered-skill name conflicts with an existing object. It SHALL NOT infer replacement or update authority from matching names.

Structured and plain output SHALL distinguish errors that block apply from non-blocking warnings and SHALL identify the affected target.

#### Scenario: Existing specialist blocks create plan

- **WHEN** a new deployment resolves specialist name `payments-reviewer-specialist`
- **AND WHEN** an unrelated specialist already uses that name
- **THEN** planning reports the collision as a blocker
- **AND THEN** it makes no durable project-definition mutation

### Requirement: Apply accepts only an intact plan for the selected overlay

`houmao-mgr project agent-deployments apply --plan <plan-id>` SHALL resolve the plan only beneath the selected overlay's jobs root.

Before mutation, apply SHALL revalidate:

- plan schema and selected overlay identity;
- blueprint snapshot, normalized-input, and rendered-output digests;
- selected credential identity;
- expected catalog schema and preconditions;
- every target path and object collision.

Apply SHALL reject a missing, malformed, cross-project, modified, stale, or blocked plan.

#### Scenario: Modified rendered artifact blocks apply

- **WHEN** a staged rendered file no longer matches the digest recorded by its plan
- **THEN** apply fails before creating any deployment-owned definition
- **AND THEN** the diagnostic identifies plan integrity failure

#### Scenario: Plan from another project is rejected

- **WHEN** an operator attempts to apply a plan id that belongs to a different project overlay
- **THEN** the selected project does not resolve or apply that plan

### Requirement: Apply materializes one complete individual-agent definition

A successful creation apply SHALL atomically materialize:

- one deployment-owned specialist;
- one deployment-owned specialist-backed project profile;
- every declared profile-private or project-registered skill;
- the declared specialist prompt, profile overlay, and memo seed;
- one canonical deployment record and managed normalized-input content.

The generated profile SHALL reference the generated specialist and all generated skill material through maintained project catalog relationships. Generated private skills SHALL remain complete static directories under the deployment-owned content root. Apply SHALL use transaction-aware internal services rather than recursively invoking Click command handlers.

#### Scenario: Blueprint creates a launchable profile

- **WHEN** an operator applies a valid `repository-reviewer` plan
- **THEN** the project catalog contains its deployment, specialist, and profile relationships
- **AND THEN** profile inspection resolves the rendered prompt overlay, memo seed, and private skill
- **AND THEN** normal profile-backed launch can consume the result without rendering the blueprint again

### Requirement: Deployment apply has all-or-nothing observable behavior

Apply SHALL preflight all catalog and filesystem targets, stage overlay-owned replacement content, use one catalog transaction, and retain sufficient rollback state until managed content and compatibility projection succeed.

If any catalog write, managed-content replacement, or compatibility projection step fails, apply SHALL roll back the deployment catalog mutation and SHALL restore or remove affected overlay-owned lexical artifacts so no partial deployment is reported as successful.

#### Scenario: Profile write failure rolls back specialist creation

- **WHEN** apply encounters a failure after preparing the specialist but before completing the generated profile
- **THEN** the command reports failure
- **AND THEN** neither a deployment record nor a partially created deployment-owned specialist remains visible

### Requirement: Deployment commands expose provenance and launch handoff

`agent-deployments list` SHALL enumerate canonical deployment records.

`agent-deployments get --name <deployment>` SHALL report blueprint id, version, source kind, source reference, source digest, normalized-input digest, owned specialist, owned profile, owned skills, rendered-output digests, timestamps, and current definition state.

A successful apply SHALL report the same essential provenance plus the exact maintained `houmao-mgr project agents launch --profile <profile>` command. Apply SHALL NOT execute that command or create a live managed agent.

#### Scenario: Apply stops before launch

- **WHEN** a deployment applies successfully
- **THEN** output includes the generated profile and its launch command
- **AND THEN** no managed agent is launched as part of apply

### Requirement: Doctor diagnoses deployment integrity and drift

`houmao-mgr project agent-deployments doctor --name <deployment>` SHALL validate:

- deployment catalog relationships;
- existence and digests of deployment-owned managed content;
- generated skill structure and frontmatter;
- specialist and profile references;
- source provenance when the original built-in or local source remains resolvable;
- references from unrelated objects or live agents that affect update or removal.

Doctor SHALL distinguish healthy state, source drift, output drift, and broken state. Source drift alone SHALL NOT rewrite installed outputs.

#### Scenario: Operator edit is reported as output drift

- **WHEN** an operator changes one deployment-owned generated skill after apply
- **THEN** doctor reports output drift with the changed artifact
- **AND THEN** it does not silently accept a new last-applied digest

#### Scenario: Local blueprint update is reported as source drift

- **WHEN** a deployment came from a local blueprint whose current content differs from the applied source digest
- **THEN** doctor reports source drift
- **AND THEN** the installed specialist, profile, and skills remain unchanged

### Requirement: Deployment update is explicit and drift-protected

Updating an existing deployment SHALL begin with `agent-deployments plan --update <deployment-name>`.

The update plan SHALL require the selected blueprint id to match the existing deployment and SHALL record last-applied object and content preconditions. Applying the update SHALL fail if a deployment-owned object is missing, owned output differs from its last-applied digest, or an unrelated object now references a resource that the update would replace or remove.

Houmao SHALL NOT merge operator edits or infer update authority from an ordinary creation plan.

#### Scenario: Explicit clean update succeeds

- **WHEN** an operator plans an update for an existing deployment
- **AND WHEN** every owned object still matches its last-applied state
- **THEN** apply may replace the deployment-owned outputs and advance their recorded provenance atomically

#### Scenario: Drift blocks update

- **WHEN** a deployment-owned prompt or skill differs from its last-applied digest
- **THEN** applying an update fails before overwriting that content
- **AND THEN** the operator receives a doctor-compatible drift diagnostic

### Requirement: Deployment removal respects ownership and references

`houmao-mgr project agent-deployments remove --name <deployment>` SHALL remove only objects and lexical managed paths owned by that deployment.

Removal SHALL fail before mutation when a live managed agent or an unrelated catalog object references the deployment-owned profile, specialist, or registered skill. It SHALL never follow a symlink while deleting an overlay-owned artifact path.

After successful removal, the deployment record and its unreferenced owned resources SHALL be absent, while credentials and unrelated project content SHALL remain.

#### Scenario: Live agent blocks deployment removal

- **WHEN** a live managed agent was launched from the deployment-owned profile
- **THEN** deployment removal fails before deleting the profile or specialist
- **AND THEN** the diagnostic identifies the live reference

#### Scenario: Clean deployment removal preserves credentials

- **WHEN** no live agent or unrelated catalog object references a deployment
- **THEN** removal deletes its record and owned definition content
- **AND THEN** the selected credential profile and unrelated project skills remain intact
