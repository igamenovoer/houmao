## ADDED Requirements

### Requirement: Project agents is the selected-project agent-instance facade
`houmao-mgr project [--project-dir <dir>] agents` SHALL operate on managed-agent instances that belong to the selected project overlay.

`project agents` SHALL use project-local selectors for project-owned instances, such as the project-managed instance name exposed by the project layer. It SHALL validate runtime manifest ownership before returning or mutating existing managed-agent state.

`project agents` SHALL NOT operate on an agent from another project overlay merely because that agent is visible in the shared managed-agent registry.

At minimum, maintained project-agent operations SHALL include:

- `launch`
- `list`
- `get`
- `stop`

Project-agent follow-up operations such as prompt, interrupt, relaunch, gateway, mail, mailbox, memory, or turn MAY be exposed when they retain the same selected-project ownership check before touching runtime state.

#### Scenario: Project agents list is overlay scoped
- **WHEN** `/repo-a/.houmao` and `/repo-b/.houmao` both have launched managed agents in the shared registry
- **AND WHEN** an operator runs `houmao-mgr project --project-dir /repo-a agents list`
- **THEN** the command reports only managed-agent instances whose runtime manifests belong to `/repo-a/.houmao`
- **AND THEN** it does not include `/repo-b` agents only because they are visible in the shared registry

#### Scenario: Project agents get rejects cross-project instance
- **WHEN** managed agent `worker-b` belongs to `/repo-b/.houmao`
- **AND WHEN** an operator runs `houmao-mgr project --project-dir /repo-a agents get --name worker-b`
- **THEN** the command fails clearly because the instance does not belong to the selected project overlay
- **AND THEN** it does not return global registry state for the cross-project agent

#### Scenario: Project profile launch remains project scoped
- **WHEN** project `/repo-a` has project profile `reviewer`
- **AND WHEN** an operator runs `houmao-mgr project --project-dir /repo-a agents launch --profile reviewer`
- **THEN** the command resolves `reviewer` from `/repo-a/.houmao`
- **AND THEN** the launched managed agent is recorded as belonging to `/repo-a/.houmao`
