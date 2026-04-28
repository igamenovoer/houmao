## ADDED Requirements

### Requirement: Session lifecycle includes degraded and stale recovery paths

The session-lifecycle reference page SHALL include a subsection covering degraded and stale recovery as a first-class lifecycle path. The subsection SHALL state that when a registry record claims `active` but tmux inspection reveals a broken session, `agents stop` and `agents relaunch` route through dedicated recovery helpers instead of failing with a generic unusable-target error. The subsection SHALL link to the dedicated degraded-stale recovery reference page.

#### Scenario: Reader discovers recovery from session-lifecycle page

- **WHEN** a reader reads the session-lifecycle page
- **THEN** they see recovery mentioned alongside start, resume, prompt, and stop
- **AND THEN** they can follow a link to the dedicated recovery page for full details

## MODIFIED Requirements

### Requirement: Session lifecycle documented

The run-phase reference SHALL include a page documenting `RuntimeSessionController` and the session lifecycle using the current `start_runtime_session()` and `resume_runtime_session()` behavior derived from `runtime.py`.

#### Scenario: Reader understands degraded and stale recovery in the lifecycle diagram

- **WHEN** a reader opens the session-lifecycle page and views the lifecycle diagram
- **THEN** the diagram or accompanying text indicates that `stop` and `relaunch` may route through recovery when the tmux session is degraded or stale
