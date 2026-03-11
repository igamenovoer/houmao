# cao-interactive-demo-module-structure Specification

## Purpose
Define the split-package module structure and public API contract for the interactive CAO demo.

## Requirements
### Requirement: Subpackage module layout

The `cao_interactive_full_pipeline_demo.py` monolith SHALL be decomposed into a `cao_interactive_demo/` subpackage under `src/gig_agents/demo/` containing exactly six modules: `models.py`, `cli.py`, `commands.py`, `cao_server.py`, `runtime.py`, and `rendering.py`, plus an `__init__.py` that re-exports the public API.

#### Scenario: Package directory exists with all required modules
- **WHEN** the refactoring is complete
- **THEN** the directory `src/gig_agents/demo/cao_interactive_demo/` SHALL contain exactly the files `__init__.py`, `models.py`, `cli.py`, `commands.py`, `cao_server.py`, `runtime.py`, and `rendering.py`

### Requirement: Module responsibility boundaries

Each module in the subpackage SHALL own a single cohesive concern. The internal import dependency graph SHALL be acyclic, following the order: `models` <- `rendering` <- `runtime` <- `cao_server` <- `commands` <- `cli`.

#### Scenario: models.py contains all data types and constants
- **WHEN** a developer looks for Pydantic models (`DemoState`, `TurnRecord`, `ControlInputRecord`, `VerificationTurnSummary`, `VerificationReport`, `ControlActionSummary`), dataclasses (`DemoPaths`, `DemoEnvironment`, `DemoInvocation`, `CommandResult`, `OutputTextTailResult`), type aliases (`CommandRunner`, `ProgressWriter`), or module-level constants
- **THEN** they SHALL find them in `models.py` and in no other subpackage module

#### Scenario: cli.py contains the CLI entry point and argument parsing
- **WHEN** a developer looks for `main()`, `_build_parser()`, or CLI resolution helpers (`_resolve_demo_invocation`, `_resolve_repo_root`, `_resolve_workspace_root`, `_resolve_prompt_text`, `_resolve_key_stream`)
- **THEN** they SHALL find them in `cli.py` and in no other subpackage module

#### Scenario: commands.py contains the public lifecycle functions
- **WHEN** a developer looks for `start_demo`, `send_turn`, `send_control_input`, `inspect_demo`, `verify_demo`, `stop_demo`, or state I/O helpers (`load_demo_state`, `save_demo_state`, `load_turn_records`, `load_control_records`, `require_active_state`)
- **THEN** they SHALL find them in `commands.py` and in no other subpackage module

#### Scenario: cao_server.py contains CAO server lifecycle management
- **WHEN** a developer looks for `_ensure_cao_server`, `_replace_existing_cao_server`, `_stop_cao_server_with_known_configs`, launcher config helpers, port scanning functions, or process lifecycle functions
- **THEN** they SHALL find them in `cao_server.py` and in no other subpackage module

#### Scenario: runtime.py contains brain build and session runtime functions
- **WHEN** a developer looks for `_build_brain`, `_start_runtime_session`, `_stop_remote_session`, `run_subprocess_command`, `_run_subprocess_command_with_wait_feedback`, or `_kill_tmux_session`
- **THEN** they SHALL find them in `runtime.py` and in no other subpackage module

#### Scenario: rendering.py contains output rendering and utility functions
- **WHEN** a developer looks for `_render_human_inspect_output`, `_render_start_output`, `_parse_events`, `_extract_done_message`, JSON I/O helpers, validation helpers, or formatting utilities
- **THEN** they SHALL find them in `rendering.py` and in no other subpackage module

#### Scenario: No circular imports between subpackage modules
- **WHEN** the subpackage is imported
- **THEN** no circular import error SHALL occur
- **AND** each module SHALL only import from modules earlier in the dependency chain: `models` <- `rendering` <- `runtime` <- `cao_server` <- `commands` <- `cli`

### Requirement: Legacy monolith removed and repository callers migrated

The legacy module `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` SHALL be removed after the split package is in place, and repository-owned callers SHALL use `gig_agents.demo.cao_interactive_demo` or the owning submodules instead of the deleted monolith path.

#### Scenario: Legacy module file removed
- **WHEN** the refactoring is complete
- **THEN** the path `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` SHALL not exist

#### Scenario: Demo shell wrapper invokes the split CLI module
- **WHEN** a developer inspects `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh`
- **THEN** it SHALL invoke `pixi run python -m gig_agents.demo.cao_interactive_demo.cli`

#### Scenario: Verification helper imports the canonical package
- **WHEN** a developer inspects `scripts/demo/cao-interactive-full-pipeline-demo/scripts/verify_report.py`
- **THEN** it SHALL import `FIXED_CAO_BASE_URL` from `gig_agents.demo.cao_interactive_demo`

#### Scenario: Demo tests patch owning modules directly
- **WHEN** demo unit or integration tests patch non-public helpers or collaborators
- **THEN** they SHALL patch owning submodules such as `gig_agents.demo.cao_interactive_demo.cao_server`, `gig_agents.demo.cao_interactive_demo.commands`, `gig_agents.demo.cao_interactive_demo.runtime`, or `gig_agents.demo.cao_interactive_demo.cli`
- **AND** they SHALL not target the deleted `gig_agents.demo.cao_interactive_full_pipeline_demo` module path

### Requirement: Subpackage __init__.py public API re-export

The `cao_interactive_demo/__init__.py` SHALL re-export all public symbols so that `from gig_agents.demo.cao_interactive_demo import X` works as the canonical new import path.

#### Scenario: Public API importable from subpackage
- **WHEN** a caller uses `from gig_agents.demo.cao_interactive_demo import start_demo`
- **THEN** the import SHALL succeed and return the `start_demo` function from `commands.py`

#### Scenario: Subpackage __init__.py lists explicit __all__
- **WHEN** the subpackage `__init__.py` is inspected
- **THEN** it SHALL contain an explicit `__all__` list enumerating every re-exported public symbol

### Requirement: Canonical package contract is directly validated

The canonical package surface SHALL be covered by automated tests that import from `gig_agents.demo.cao_interactive_demo` and verify explicit exports.

#### Scenario: Representative canonical imports are tested
- **WHEN** unit tests run
- **THEN** at least one focused test SHALL import `gig_agents.demo.cao_interactive_demo`
- **AND** it SHALL verify representative public symbols such as `start_demo` and `FIXED_CAO_BASE_URL`

#### Scenario: Explicit __all__ is tested
- **WHEN** unit tests inspect `gig_agents.demo.cao_interactive_demo.__all__`
- **THEN** they SHALL verify that expected exported symbols are enumerated
- **AND** those symbols SHALL resolve to the owning module definitions
