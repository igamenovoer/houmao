## ADDED Requirements

### Requirement: Specialist and project-profile work is an admin protected route
Maintained specialist, project-profile, launch-dossier, recipe, fast-forward creation, easy launch, and easy stop guidance SHALL be owned by protected `houmao-agent-definition` and SHALL be eligible through `houmao-admin-entrypoint`.

The public admin route SHALL preserve its admin actor frame and explicit project target. The system SHALL NOT install an independent `houmao-create-specialist` or `houmao-specialist-mgr` public skill.

#### Scenario: Human asks to create a specialist
- **WHEN** a human invokes the admin entrypoint with an explicit project and specialist creation request
- **THEN** the entrypoint routes to protected `houmao-agent-definition`
- **AND THEN** the unified specialist behavior prepares the supported command without a compatibility wrapper

## MODIFIED Requirements

### Requirement: `houmao-specialist-mgr` is no longer the canonical specialist-management skill
The system SHALL treat protected `houmao-agent-definition` as the sole current system-skill owner for specialist and project-profile authoring.

`houmao-specialist-mgr` SHALL NOT remain packaged as a public skill, protected routine, alias, or compatibility wrapper. Migration diagnostics MAY name it only to direct users to `$houmao-admin-entrypoint agent-definition ...`.

#### Scenario: Old specialist wrapper invocation is encountered
- **WHEN** a user or migration check refers to `houmao-specialist-mgr`
- **THEN** Houmao identifies the admin entrypoint's agent-definition route as the replacement
- **AND THEN** it does not install or execute a compatibility wrapper

## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-create-specialist` system skill
**Reason**: Independent specialist-management packaging is removed.
**Migration**: Use the admin entrypoint's protected agent-definition route.

### Requirement: `houmao-create-specialist` treats credential defaults as display-name defaults only
**Reason**: This behavior is now owned by unified agent-definition guidance.
**Migration**: Preserve the rule in the protected specialist command owned by `houmao-agent-definition`.

### Requirement: `houmao-create-specialist` resolves the `houmao-mgr` launcher in the required precedence order
**Reason**: Launcher resolution is no longer owned by a standalone specialist skill.
**Migration**: Preserve supported launcher resolution in the protected agent-definition routine.

### Requirement: `houmao-create-specialist` recovers explicit inputs from conversation context and asks before guessing
**Reason**: Actor-aware admin routing and unified agent-definition guidance own input recovery.
**Migration**: Apply the admin target and required/optional input contracts before the protected command runs.

### Requirement: `houmao-create-specialist` describes Claude credential lanes separately from optional state templates
**Reason**: Provider-specific specialist guidance belongs to the unified protected routine.
**Migration**: Keep the distinction in agent-definition references.

### Requirement: `houmao-create-specialist` explains filesystem mailbox behavior on specialist-backed easy launch
**Reason**: Easy-launch behavior belongs to unified agent-definition guidance.
**Migration**: Preserve the behavior in the protected easy-launch command.

### Requirement: `houmao-specialist-mgr` routes project-profile editing commands
**Reason**: The compatibility wrapper is removed.
**Migration**: Route project-profile editing through protected `houmao-agent-definition`.

### Requirement: `houmao-specialist-mgr` routes specialist update requests
**Reason**: The compatibility wrapper is removed.
**Migration**: Route specialist updates through protected `houmao-agent-definition`.

### Requirement: `houmao-specialist-mgr` preserves foreground-first launch-time gateway posture
**Reason**: The compatibility wrapper is removed.
**Migration**: Preserve the posture in the protected agent-definition launch command.

### Requirement: `houmao-specialist-mgr` ships per-tool credential kinds references and cites them when asking the user for missing auth inputs
**Reason**: References move to the canonical protected routine.
**Migration**: Place maintained credential-kind references under `houmao-agent-definition` ownership.

### Requirement: `houmao-specialist-mgr` compatibility wrapper routes renamed agent-definition subcommands
**Reason**: No public compatibility wrapper remains.
**Migration**: Invoke the canonical agent-definition route directly through the admin entrypoint.

### Requirement: `houmao-specialist-mgr` delegates supported command authoring to config drafts and direct snippets
**Reason**: Delegation through a compatibility layer is removed.
**Migration**: Keep config-draft and direct-snippet behavior inside protected `houmao-agent-definition`.

