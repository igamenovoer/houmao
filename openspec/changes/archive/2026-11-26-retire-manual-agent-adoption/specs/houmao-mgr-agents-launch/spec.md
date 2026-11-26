## MODIFIED Requirements

### Requirement: Managed-agent birth is source-scoped rather than global management
The maintained global managed-agent management surface SHALL NOT expose a first-birth launch command.

Project-backed managed-agent birth SHALL be represented by:

```text
houmao-mgr project [--project-dir <dir>] agents launch
```

Direct native/provider construction plumbing, when retained, SHALL live under internal native-agent command surfaces rather than `houmao-mgr agents global`.

A supported Houmao launch SHALL establish local managed-agent identity and lifecycle authority.

#### Scenario: Global management omits launch
- **WHEN** an operator runs `houmao-mgr agents global --help`
- **THEN** the help output does not list `launch`
- **AND THEN** the operator must choose a source-scoped managed launch to create a local managed agent

#### Scenario: Project launch remains public birth path
- **WHEN** an operator wants to create a managed agent from project profile `reviewer`
- **THEN** the maintained command path is `houmao-mgr project agents launch --profile reviewer`
- **AND THEN** the launch resolves source definitions from the selected project overlay rather than from global registry state
