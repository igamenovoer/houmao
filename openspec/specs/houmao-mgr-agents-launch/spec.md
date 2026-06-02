# houmao-mgr-agents-launch Specification

## Purpose
Define retained managed-agent birth contracts for project-backed launch and internal native construction without requiring `houmao-server`.
## Requirements
### Requirement: Managed launch establishes primary tmux surface independent of user base indexes
Retained managed-agent birth surfaces such as `houmao-mgr project agents launch` SHALL start Houmao-owned tmux-backed managed-agent sessions successfully when the user's tmux configuration sets non-zero default window or pane base indexes, provided tmux otherwise supports creating and moving the session's bootstrap surface.

For launched tmux-backed sessions, the command SHALL publish managed-agent metadata only after the runtime has established the contractual primary window index `0` and captured the primary tmux object handles needed for later operations.

If the primary surface cannot be established, launch SHALL fail before publishing an active shared-registry record for the attempted managed agent.

#### Scenario: Launch succeeds with one-based tmux indexes
- **WHEN** an operator's tmux configuration sets `base-index 1` and `pane-base-index 1`
- **AND WHEN** the operator runs `houmao-mgr project agents launch` for a local tmux-backed provider
- **THEN** the launched managed-agent session owns primary window index `0`
- **AND THEN** the manifest records primary tmux object handles for the managed-agent surface
- **AND THEN** later prompt, capture, interrupt, gateway, and relaunch operations can target that primary surface without relying on `session:0.0`

#### Scenario: Failed primary-surface preparation does not publish active launch metadata
- **WHEN** a retained managed-agent birth command creates a tmux session but cannot establish the managed-agent primary window at index `0`
- **THEN** the command reports launch failure
- **AND THEN** it does not publish an active lifecycle-aware managed-agent registry record for that failed launch

### Requirement: Agent relaunch CLI surface provides a command-template entry
The CLI-owned command-template registry SHALL provide template entries for selected-agent relaunch through `houmao-mgr agents single --agent-id <id> relaunch` or `houmao-mgr agents single --agent-name <name> relaunch`, and for current-session active refresh through `houmao-mgr agents self relaunch`.

The selected-agent relaunch templates SHALL describe group-level agent selectors, explicit chat-session mode fields, explicit chat-session id fields, and conflicts between mutually exclusive chat-session policies.

#### Scenario: Relaunch omits chat-session policy by default
- **WHEN** an agent renders `agents.single.relaunch` with an explicit agent name but no explicit chat-session policy
- **THEN** the rendered argv includes the agent selector
- **AND THEN** chat-session mode and chat-session id options remain absent

#### Scenario: Relaunch chat-session conflict blocks rendering
- **WHEN** an agent renders `agents.single.relaunch` with conflicting chat-session policy fields
- **THEN** the renderer reports a blocker
- **AND THEN** it does not return executable argv

### Requirement: Managed-agent birth is source-scoped rather than global management
The maintained global managed-agent management surface SHALL NOT expose a first-birth launch command.

Project-backed managed-agent birth SHALL be represented by:

```text
houmao-mgr project [--project-dir <dir>] agents launch
```

Direct native/provider construction plumbing, when retained, SHALL live under internal native-agent command surfaces rather than `houmao-mgr agents global`.

Existing local managed-agent identities MAY be adopted into the registry through `houmao-mgr agents self join` when the target is the caller's current tmux session.

#### Scenario: Global management omits launch
- **WHEN** an operator runs `houmao-mgr agents global --help`
- **THEN** the help output does not list `launch`
- **AND THEN** the operator must choose a source-scoped birth command or a join/import command instead

#### Scenario: Project launch remains public birth path
- **WHEN** an operator wants to create a managed agent from project profile `reviewer`
- **THEN** the maintained command path is `houmao-mgr project agents launch --profile reviewer`
- **AND THEN** the launch resolves source definitions from the selected project overlay rather than from global registry state
