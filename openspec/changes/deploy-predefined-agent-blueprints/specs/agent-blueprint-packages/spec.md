## ADDED Requirements

### Requirement: Agent blueprints use a versioned portable package contract

Houmao SHALL define an agent blueprint as a self-contained directory whose root contains `blueprint.toml`.

The manifest SHALL declare at minimum:

- `schema_version = "houmao-agent-blueprint.v1"`;
- a stable blueprint id;
- a blueprint version;
- a human-readable purpose;
- one or more supported Houmao tool families;
- zero or more typed task inputs;
- the declared specialist, profile, memo, and skill outputs that the package provides.

Package-relative output paths SHALL resolve beneath the blueprint root. The package MAY contain `README.md`, `templates/`, `skills/`, and `references/`, but directory names alone SHALL NOT imply an output that the manifest does not declare.

#### Scenario: Valid local blueprint is inspected

- **WHEN** an operator supplies a local directory with a valid v1 manifest and all declared members
- **THEN** Houmao loads the directory as one agent blueprint
- **AND THEN** inspection reports its id, version, purpose, supported tools, inputs, outputs, and content digest

#### Scenario: Unsupported blueprint schema is rejected

- **WHEN** a blueprint manifest declares an unsupported schema version
- **THEN** Houmao rejects the package before rendering any member
- **AND THEN** the diagnostic identifies the unsupported schema value

### Requirement: Blueprint inputs are typed and bounded

A v1 blueprint input SHALL use one of these types: `string`, `markdown`, `string-list`, or `boolean`.

Each declaration SHALL provide a unique field name and required or optional state. It MAY provide authoring guidance and a non-secret default whose value matches the declared type.

The normalized deployment input document SHALL contain only manifest-declared fields with values matching their declared types. Houmao SHALL reject missing required fields, unknown fields, duplicate declarations, and type mismatches.

Tool, credential, workdir, model, reasoning level, mailbox selection, prompt mode, and headless posture SHALL remain maintained deployment settings rather than unconstrained task-input fields.

#### Scenario: Typed task inputs validate

- **WHEN** a blueprint requires Markdown field `task.objective` and string-list field `task.done_when`
- **AND WHEN** the normalized input document provides values of those types
- **THEN** Houmao accepts the input document for rendering

#### Scenario: Unknown task field is rejected

- **WHEN** a normalized input document supplies a field not declared by the selected blueprint
- **THEN** Houmao rejects the input document
- **AND THEN** it does not let that field control output names, paths, credentials, or launch settings

### Requirement: Blueprint rendering is strict and non-executable

Blueprint text templates SHALL use field placeholders in the namespace `{{houmao.input.<field-name>}}`.

The renderer SHALL perform exact declared-field lookup and deterministic type-aware text formatting. It SHALL NOT evaluate Python, shell, environment expansion, Jinja expressions, arbitrary attribute access, filters, includes, executable hooks, or blueprint-provided programs.

The renderer SHALL fail when a template references an unknown field, a required value is absent, a value cannot be rendered according to its declared type, or a placeholder remains unresolved after rendering.

#### Scenario: Declared placeholder renders deterministically

- **WHEN** a template contains `{{houmao.input.task.objective}}`
- **AND WHEN** the normalized input document contains the declared objective
- **THEN** the rendered file contains that objective in place of the placeholder
- **AND THEN** repeated rendering of the same blueprint snapshot and inputs produces the same content digest

#### Scenario: Expression-like placeholder is rejected

- **WHEN** a blueprint contains a placeholder that requests a filter, expression, environment variable, or undeclared attribute
- **THEN** Houmao rejects the blueprint or render
- **AND THEN** it does not evaluate the expression

### Requirement: Blueprint package reads are confined and data-only

Houmao SHALL treat built-in and local blueprint packages as untrusted data.

Validation SHALL reject:

- absolute or parent-traversing member paths;
- members that resolve outside the lexical blueprint root;
- symlinks;
- device files, sockets, and other non-regular members;
- duplicate output names or paths;
- undeclared binary templates;
- package members that exceed maintained size or count limits.

Houmao SHALL copy an accepted source into a plan-owned snapshot before rendering and SHALL compute a deterministic source digest from that snapshot. It SHALL never execute a blueprint member.

#### Scenario: Symlinked package member is rejected

- **WHEN** a local blueprint contains a symlink beneath a declared template or skill path
- **THEN** Houmao rejects the package
- **AND THEN** it does not read or mutate the symlink target

#### Scenario: Local source changes after planning

- **WHEN** an operator modifies the original local blueprint after Houmao created a plan snapshot
- **THEN** the existing plan continues to identify the snapshotted source digest
- **AND THEN** applying that plan does not read the modified original directory as replacement content

### Requirement: Blueprint skills materialize as complete static Agent Skills

Each blueprint-declared skill SHALL identify one directory containing a valid `SKILL.md`, a valid skill name, and any package-owned `commands/`, `references/`, `assets/`, or other static resources required by that skill.

The blueprint manifest SHALL declare whether each skill becomes a profile-private skill or a project-registered skill. Houmao SHALL validate generated frontmatter, duplicate names, output paths, and reserved Houmao system-skill names before deployment.

All placeholders in a generated skill SHALL be resolved during planning. Managed-agent launch SHALL consume the installed complete skill directory and SHALL NOT compose, generate, or rewrite that skill at runtime.

#### Scenario: Task-specific private skill is rendered before apply

- **WHEN** a blueprint declares a profile-private skill whose `SKILL.md` contains task placeholders
- **THEN** planning renders and validates a complete static skill directory
- **AND THEN** applying the plan attaches that directory to the generated profile as a private skill

#### Scenario: Reserved system-skill name is rejected

- **WHEN** a blueprint output attempts to create a generated skill with a Houmao-reserved system-skill name
- **THEN** validation fails before project definition mutation

### Requirement: Houmao resolves built-in and explicit local blueprint sources

Houmao SHALL package built-in agent blueprints separately from system skills and native-agent starter assets.

The source designator `builtin:<id>` SHALL resolve one packaged built-in by exact id. An explicit local-directory source SHALL resolve only the supplied directory. Houmao SHALL NOT search arbitrary workspaces or fetch network content while resolving either source.

Built-in and local sources SHALL use the same manifest, safety, rendering, and digest rules.

#### Scenario: Built-in blueprint is listed

- **WHEN** an operator lists available agent blueprints
- **THEN** Houmao reports every packaged built-in blueprint with its id, version, and purpose
- **AND THEN** it does not claim that unregistered local directories are part of the built-in list

#### Scenario: Missing built-in id fails clearly

- **WHEN** an operator requests `builtin:missing-blueprint`
- **THEN** Houmao fails without falling back to a similarly named local directory or network source

### Requirement: Houmao ships a validating reference blueprint

The built-in blueprint collection SHALL include a `repository-reviewer` blueprint that exercises:

- a specialist prompt;
- a profile prompt overlay;
- a memo seed;
- at least one profile-private skill;
- required task objective and completion-criteria inputs.

The reference blueprint SHALL pass the same validator and renderer used for operator-supplied local blueprints.

#### Scenario: Reference blueprint can be planned

- **WHEN** an operator supplies valid task inputs and maintained runtime selections for `builtin:repository-reviewer`
- **THEN** Houmao can produce a valid deployment plan from that built-in
- **AND THEN** every generated skill is complete before the plan becomes applicable

### Requirement: Blueprint inputs and files do not carry credentials

Blueprint manifests, normalized task inputs, templates, skills, references, source snapshots, and rendered outputs SHALL NOT be used to store credential secrets.

Credential selection SHALL occur through the maintained project credential display-name input to deployment planning. Houmao SHALL keep the referenced credential's protected content outside the blueprint snapshot and rendered deployment tree.

#### Scenario: Deployment selects an existing credential separately

- **WHEN** an operator plans a Codex blueprint deployment using credential display name `reviewer-creds`
- **THEN** the plan records the selected catalog credential identity without copying its secret content into the blueprint inputs or rendered outputs
