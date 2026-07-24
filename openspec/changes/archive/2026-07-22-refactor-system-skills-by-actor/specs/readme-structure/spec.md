## ADDED Requirements

### Requirement: README system-skill examples preserve the actor boundary
Every README system-skill example SHALL make clear whether the user's CLI assistant is acting for the human through the admin entrypoint or whether a managed Houmao agent is acting through the agent entrypoint.

Examples SHALL use public skill invocations and SHALL NOT rely on a protected logical id as a top-level trigger.

#### Scenario: README shows a managed-agent mailbox example
- **WHEN** the README demonstrates mailbox work performed by a managed agent
- **THEN** the example begins through `$houmao-agent-entrypoint`
- **AND THEN** it does not make the reader invoke the protected mailbox routine directly

## MODIFIED Requirements

### Requirement: Drive with Your CLI Agent is step 1
The README Quick Start SHALL present the skill-driven human-operator path as the primary recommended entry point. It SHALL instruct the user to install Houmao, verify `tmux`, install the admin system-skill pack into the target CLI-agent home with `houmao-mgr system-skills install --tool <tool> --pack admin`, start that CLI agent from the target directory, and invoke `$houmao-admin-welcome start-guided-tour`.

The README SHALL explain that the welcome is read-only and hands executable work to `$houmao-admin-entrypoint ...`. It SHALL keep detailed pack, home, mode, migration, and receipt behavior in linked documentation and SHALL NOT recommend direct installation from the source asset tree, old named sets, protected routine selectors, or `$houmao-touring`.

#### Scenario: User follows the preferred admin-pack path
- **WHEN** a user reads the Quick Start
- **THEN** they see the Houmao-owned admin-pack installation command
- **AND THEN** their first guided prompt uses `houmao-admin-welcome`
- **AND THEN** they understand that execution transfers to the admin entrypoint

#### Scenario: User needs installation detail
- **WHEN** a user needs an explicit home, symlink mode, upgrade, or conflict resolution
- **THEN** the README links to the system-skills reference
- **AND THEN** it does not expand the full lifecycle flag reference inline

#### Scenario: User follows the preferred skill install path
- **WHEN** a user reads the Quick Start on a machine with `npx` and internet access
- **THEN** they see `npx skills add igamenovoer/tool-skills/houmao` as the preferred system-skill installation command
- **AND THEN** they understand that `houmao-touring` is the first guided workflow to ask their CLI agent to run

#### Scenario: User needs the Houmao-owned installer
- **WHEN** a user reads the Quick Start without `npx`, without internet access, or with explicit projection needs
- **THEN** they see `houmao-mgr system-skills install --tool <tool>[,<tool>...]` as the supported fallback or custom installation path
- **AND THEN** the README keeps detailed flag behavior in linked docs rather than expanding it inline


### Requirement: System Skills section lists every shipped skill with its purpose
The README System Skills section SHALL be a concise summary of the three public roles and the actor-driven model, not a table of protected routines.

It SHALL explain that the admin welcome orients the human, the admin entrypoint performs human-directed work against explicit targets, and the agent entrypoint performs verified managed-agent work. It SHALL state that project, specialist/profile, messaging, gateway, mailbox, memory, inspection, workspace, interop, and loop behavior is nested protected implementation and SHALL link to the System Skills Overview for the complete route map.

#### Scenario: Reader sees skills as an actor-qualified capability layer
- **WHEN** a reader scans the System Skills section
- **THEN** they understand the three public roles and which actor each serves
- **AND THEN** they see a link to protected routine detail instead of a long flat catalog

#### Scenario: Reader sees skills as an agent capability layer
- **WHEN** a reader scans the System Skills section
- **THEN** they understand that skills let the CLI agent operate Houmao on the user's behalf
- **AND THEN** they see a link to the full System Skills Overview instead of a long inline catalog


## REMOVED Requirements

### Requirement: README skill table uses unified agent-definition row
**Reason**: README no longer uses a table of low-level system skills.
**Migration**: Mention agent-definition as a protected owner only when a public admin-entrypoint workflow needs it.
