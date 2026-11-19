# Spec Delta

## Purpose

Define how a Houmao launch selects a native interaction and process lifetime, and what operators can inspect or attach to after launch.

## ADDED Requirements

### Requirement: Run mode describes the selected native entrypoint

Houmao SHALL identify a managed launch with exactly one run mode. Headless executes one native CLI process per accepted prompt. Service keeps a native protocol host alive across requests. TUI presents a native terminal UI. Web presents the tool's native browser application.

#### Scenario: Logical history survives one-shot execution

- **WHEN** two headless requests continue a saved conversation
- **THEN** the second request starts a new native worker and uses the selected native conversation identity

#### Scenario: A Web application exposes a control API

- **WHEN** a browser host also accepts structured requests
- **THEN** its run mode is web and the adapter reports its supported control operations separately

### Requirement: Selection resolves only a qualified tool and mode

Every managed birth path SHALL resolve the direct selection, stored launch default, or documented entrypoint default to one qualified tool/mode/backend combination. Preflight SHALL reject unsupported combinations before modifying a home, taking over a predecessor, or publishing an agent.

#### Scenario: An operator selects a terminal for DSH

- **WHEN** an operator explicitly requests DSH in tui mode on the supported reference build
- **THEN** launch reports the supported modes and leaves the intended predecessor and its home intact

#### Scenario: Default follows the birth surface

- **WHEN** a project launch omits direct and stored mode
- **THEN** Claude, Codex, and Kimi select tui and DSH selects web
- **AND** a passive headless birth explicitly selects headless and validates that pair

### Requirement: Run mode and operator handoff are independent

The stored mode SHALL select the native entrypoint independently of prompt policy, executor, gateway attachment, or caller terminal availability. Terminal handoff and key control require a verified terminal surface. Web handoff SHALL expose a safe browser origin and bound session, with browser opening under explicit operator control.

#### Scenario: A Web host has a tmux supervisor

- **WHEN** a Web launch completes from an interactive terminal
- **THEN** the manager reports the browser surface and safe connection information and keeps its log pane out of terminal handoff

#### Scenario: A TUI starts without an interactive caller

- **WHEN** a script launches a supported TUI with unattended policy
- **THEN** the TUI starts under the configured supervisor and the launch result identifies how an operator can attach

### Requirement: Run mode belongs to the managed instance

Inspection and relaunch SHALL use the persisted mode and concrete backend for the selected execution owner. Changing a profile default affects future births. Unsupported historical runtime schemas SHALL produce fresh-launch guidance.

#### Scenario: A profile changes after birth

- **WHEN** a profile changes from tui to service and an operator relaunches its existing TUI instance
- **THEN** the existing agent relaunches in its recorded tui mode

#### Scenario: A legacy ACP record is selected

- **WHEN** a retained RC2 per-turn ACP manifest is read by the new runtime
- **THEN** the operator receives the schema diagnostic and the record confers no service ownership
