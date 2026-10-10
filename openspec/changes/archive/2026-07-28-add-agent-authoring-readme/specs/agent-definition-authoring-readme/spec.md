## ADDED Requirements

### Requirement: Skill-authored workspaces contain a root README

The Houmao Agent Definition authoring workflow SHALL create `<authoring-dir>/README.md` when a skill initializes a new workspace or resumes an existing workspace that lacks the file. It SHALL refresh the README before every user-facing authoring stop, review boundary, or handoff.

#### Scenario: New workspace receives orientation

- **WHEN** the authoring skill initializes an Agent Definition workspace
- **THEN** the workspace root contains `README.md` alongside `intent/`
- **AND THEN** `intent/src/agent-def-overview.md` remains the only required source-intent file

#### Scenario: Partial derivation remains understandable

- **WHEN** the workflow derives a workspace and stops before approval
- **THEN** the root README reports the current derived-but-unapproved lifecycle state
- **AND THEN** it inventories the source and derived files that actually exist

#### Scenario: Existing workspace is resumed

- **WHEN** the authoring skill resumes an existing workspace without a root README
- **THEN** it creates the README before returning control to the user

### Requirement: The authoring README explains the complete current workspace

The generated README SHALL identify the agent and its purpose, report current lifecycle state, show the actual relative directory tree, and list every regular file beneath the authoring root with a concise explanation and relative link. When a validated revision exists, it SHALL include the definition id, revision id, revision digest, and instance-contract digest.

#### Scenario: Materialized workspace is ready for handoff

- **WHEN** the workspace contains a validated revision under `agent-definition/`
- **THEN** the README explains `intent/src`, `intent/derived`, `agent-definition`, and its own generated role
- **AND THEN** it lists the revision identity and validation digests
- **AND THEN** it explains how to continue authoring, validate, deploy, or distribute the workspace

#### Scenario: Inventory reflects actual files

- **WHEN** the authoring route refreshes the README
- **THEN** its current-tree and file-inventory sections include every regular file that exists beneath the authoring root
- **AND THEN** they do not present an absent future artifact as a current file

### Requirement: The authoring README is portable non-authoritative orientation

The README SHALL state that it is generated orientation rather than source intent, derived authority, approval evidence, or immutable revision content. It SHALL use relative workspace paths and SHALL NOT contain credentials, secret values, absolute machine paths, or temporary external source paths.

#### Scenario: README changes do not change contract freshness

- **WHEN** the root README is created or refreshed
- **THEN** source, derived, approval, and revision digests remain governed by their existing artifact sets
- **AND THEN** changing a requirement still requires editing `intent/src` and repeating the authoring lifecycle

#### Scenario: Revision is materialized externally

- **WHEN** the user explicitly selects an output outside the authoring workspace
- **THEN** the README may record portable revision identity and digest facts
- **AND THEN** it does not serialize the absolute external path or claim that the revision is bundled inside the workspace

### Requirement: Workspace-local revision output is the skill default

The authoring skill SHALL use `<authoring-dir>/agent-definition` when the user does not explicitly select another immutable revision output.

#### Scenario: User omits materialization output

- **WHEN** the user approves materialization without naming an output path
- **THEN** the skill uses the maintained CLI default under `<authoring-dir>/agent-definition`
- **AND THEN** the refreshed README inventories that bundled revision
