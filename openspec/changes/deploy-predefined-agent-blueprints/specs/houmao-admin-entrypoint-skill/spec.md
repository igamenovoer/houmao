## ADDED Requirements

### Requirement: Admin entrypoint routes agent blueprint deployment intent

The public `houmao-admin-entrypoint` SHALL recognize human-operator requests to deploy, instantiate, materialize, or prepare one individual agent from a predefined built-in or explicit local agent blueprint.

It SHALL route that intent through:

```text
houmao-admin-entrypoint->houmao-shared-routines->houmao-agent-definition->deploy-blueprint()
```

The route SHALL establish the immutable admin actor frame and selected project before protected definition mutation. The entrypoint SHALL treat natural-language intent as sufficient for route selection even when the user does not name the `deploy-blueprint` subcommand.

#### Scenario: Natural-language blueprint request routes implicitly

- **WHEN** a human asks the admin assistant to create a repository reviewer from a predefined Houmao agent
- **THEN** the entrypoint selects the agent-definition blueprint deployment route
- **AND THEN** it does not require the human to know the internal subcommand name

#### Scenario: Explicit local blueprint remains an admin route

- **WHEN** a human supplies a local blueprint directory and asks Houmao to prepare an agent for a task
- **THEN** the entrypoint passes the explicit source, project, and task context to the admin-only definition routine
- **AND THEN** it does not reinterpret the current assistant session as the managed agent being created

### Requirement: Admin entrypoint keeps blueprint deployment separate from live launch

The admin entrypoint SHALL classify blueprint deployment as definition authoring. It SHALL route a later explicit launch request through `houmao-agent-instance` or the maintained limited launch handoff only after deployment completes.

It SHALL NOT infer live-agent launch authority from a request that only asks to deploy or prepare a blueprint-backed definition.

#### Scenario: Prepare request does not launch

- **WHEN** a human asks the admin entrypoint to prepare a blueprint-backed agent
- **THEN** the routed workflow may create and validate the persisted definition
- **AND THEN** no live agent is launched unless the human makes a separate explicit launch request
