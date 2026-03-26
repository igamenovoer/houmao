## ADDED Requirements

### Requirement: LaunchPlan composition documented

The run-phase reference SHALL include a page documenting `LaunchPlan` composition: how `build_launch_plan()` takes a `LaunchPlanRequest` (brain_manifest + role_package + backend + working_directory) and produces a `LaunchPlan` with backend-specific launch arguments. Content SHALL be derived from `launch_plan.py` docstrings.

#### Scenario: Reader understands launch plan resolution

- **WHEN** a reader opens the launch-plan page
- **THEN** they find the `LaunchPlanRequest` fields, the resolution logic (env vars, launch overrides, mailbox bindings, role injection), and the resulting `LaunchPlan` structure

### Requirement: Session lifecycle documented

The run-phase reference SHALL include a page documenting `RuntimeSessionController` and the session lifecycle: `start_runtime_session()`, `resume_runtime_session()`, `send_prompt()`, `stop_session()`, session manifest persistence, and job directory management. Content SHALL be derived from `runtime.py` docstrings.

#### Scenario: Reader understands session state transitions

- **WHEN** a reader opens the session-lifecycle page
- **THEN** they find the start → running → prompt → complete lifecycle with manifest persistence points

### Requirement: Backend model documented with per-backend notes

The run-phase reference SHALL include a page documenting the `BackendKind` type and each backend implementation: `local_interactive` (tmux-backed, primary), `claude_headless`, `codex_headless`, `gemini_headless`, `codex_app_server` (headless alternatives), `cao_rest` (legacy), and `houmao_server_rest` (legacy). Content SHALL be derived from `models.py` and per-backend module docstrings.

#### Scenario: local_interactive presented as primary

- **WHEN** a reader opens the backends page
- **THEN** `local_interactive` is the first and most detailed backend described, with headless backends next, and CAO-backed backends last with a "legacy" label

#### Scenario: Backend selection logic explained

- **WHEN** the backends page describes backend resolution
- **THEN** it explains `backend_for_tool()` mapping and how `LaunchPlan.backend` is determined

### Requirement: Role injection documented per backend

The run-phase reference SHALL include a page documenting role injection: how `plan_role_injection()` produces a `RoleInjectionPlan` with backend-specific strategies (Codex → native developer instructions, Claude → appended system prompt + bootstrap message, Gemini → bootstrap message, CAO/server → profile-based injection). Content SHALL be derived from `launch_plan.py` role injection logic.

#### Scenario: Reader understands why role injection differs by backend

- **WHEN** a reader opens the role-injection page
- **THEN** they find a table or list mapping each backend to its injection method with a rationale for the difference
