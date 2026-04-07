## ADDED Requirements

### Requirement: Launch templates are reusable operator-owned instantiation definitions
The system SHALL support a named launch-template object that is distinct from reusable source definitions and distinct from live managed-agent instances.

Each launch template SHALL reference exactly one reusable source, and that source SHALL be either:
- a project-local specialist, or
- a low-level recipe resource.

Persisting, listing, inspecting, or removing a launch template SHALL NOT by itself create, stop, or mutate a live managed-agent instance.

#### Scenario: Template binds one easy specialist without creating an instance
- **WHEN** an operator creates launch template `alice` targeting specialist `cuda-coder`
- **THEN** the system persists `alice` as reusable launch configuration
- **AND THEN** it does not create a live managed-agent instance only because the template was created

#### Scenario: Template binds one low-level recipe without duplicating the source recipe
- **WHEN** an operator creates launch template `nightly-ci` targeting low-level recipe `cuda-coder-codex-default`
- **THEN** the system persists `nightly-ci` as a separate reusable launch-template object
- **AND THEN** it does not clone or rewrite the referenced recipe as part of that template creation

### Requirement: Project-local launch templates have a stable named compatibility projection
The system SHALL expose project-local launch templates through a stable named compatibility projection under:

```text
.houmao/agents/launch-templates/<name>.yaml
```

Catalog-backed or easy-authored launch templates SHALL project into that same compatibility tree so low-level inspection and launch resolution can address one stable named resource.

#### Scenario: Catalog-backed template projects into the launch-template tree
- **WHEN** a project-local launch template named `alice` exists in the authoritative catalog
- **THEN** the system materializes a compatibility resource at `.houmao/agents/launch-templates/alice.yaml`
- **AND THEN** low-level launch-template inspection can resolve the same named template through that projected path

### Requirement: Launch templates capture durable launch-time defaults
Launch templates SHALL support durable launch-time defaults without embedding secrets inline.

At minimum, a launch template SHALL support:
- source reference
- default managed-agent identity
- working directory
- auth override by reference
- operator prompt-mode override
- durable non-secret env records
- declarative mailbox configuration
- launch posture such as headless or gateway defaults
- prompt overlay

Prompt overlay SHALL support at minimum:
- `append`, which appends template-owned prompt text after the source role prompt
- `replace`, which replaces the source role prompt with template-owned prompt text

#### Scenario: Template inspection reports stored launch defaults
- **WHEN** launch template `alice` stores default agent name, workdir, auth override, mailbox config, and gateway posture
- **AND WHEN** an operator inspects that template
- **THEN** the inspection output reports those stored launch defaults as template-owned configuration
- **AND THEN** the output does not expose secret credential values inline

#### Scenario: Template prompt overlay is limited to append-or-replace semantics
- **WHEN** launch template `alice` stores a prompt overlay with `mode: append`
- **THEN** the stored template records append semantics plus the overlay text
- **AND THEN** the system does not reinterpret that overlay as arbitrary multi-stage template substitution logic

### Requirement: Launch-template resolution applies explicit precedence
The system SHALL resolve effective launch inputs with this precedence order:

1. tool-adapter defaults
2. source recipe defaults
3. launch-template defaults
4. direct CLI launch overrides
5. live runtime mutations

Fields omitted by a higher-priority layer SHALL survive from the next lower-priority layer.

Live runtime mutations such as late mailbox registration SHALL remain runtime-owned and SHALL NOT rewrite the stored launch template.

#### Scenario: Direct launch override wins over template workdir
- **WHEN** launch template `alice` stores working directory `/repos/alice`
- **AND WHEN** an operator launches from `alice` with an explicit launch-time workdir override of `/tmp/override`
- **THEN** the launched runtime uses `/tmp/override` as the effective workdir
- **AND THEN** the stored launch template still records `/repos/alice` as its reusable default

#### Scenario: Runtime mailbox mutation does not rewrite the template
- **WHEN** a running instance was launched from template `alice`
- **AND WHEN** the operator later changes that running instance's mailbox binding through a runtime mailbox mutation path
- **THEN** the running instance reflects the updated mailbox binding
- **AND THEN** the stored launch template `alice` is not silently rewritten by that runtime-only mutation
