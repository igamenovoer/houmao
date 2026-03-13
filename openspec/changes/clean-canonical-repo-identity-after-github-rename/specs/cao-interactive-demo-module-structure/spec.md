## MODIFIED Requirements

### Requirement: Subpackage module layout

The `cao_interactive_full_pipeline_demo.py` monolith SHALL be decomposed into a `cao_interactive_demo/` subpackage under `src/houmao/demo/` containing exactly six modules: `models.py`, `cli.py`, `commands.py`, `cao_server.py`, `runtime.py`, and `rendering.py`, plus an `__init__.py` that re-exports the public API.

#### Scenario: Package directory exists with all required modules
- **WHEN** the refactoring is complete
- **THEN** the directory `src/houmao/demo/cao_interactive_demo/` SHALL contain exactly the files `__init__.py`, `models.py`, `cli.py`, `commands.py`, `cao_server.py`, `runtime.py`, and `rendering.py`

### Requirement: Legacy monolith removed and repository callers migrated

The legacy module `src/houmao/demo/cao_interactive_full_pipeline_demo.py` SHALL be removed after the split package is in place, and repository-owned callers SHALL use `houmao.demo.cao_interactive_demo` or the owning submodules instead of the deleted monolith path.

#### Scenario: Legacy module file removed
- **WHEN** the refactoring is complete
- **THEN** the path `src/houmao/demo/cao_interactive_full_pipeline_demo.py` SHALL not exist

#### Scenario: Demo shell wrapper invokes the split CLI module
- **WHEN** a developer inspects `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh`
- **THEN** it SHALL invoke `pixi run python -m houmao.demo.cao_interactive_demo.cli`

#### Scenario: Verification helper imports the canonical package
- **WHEN** a developer inspects `scripts/demo/cao-interactive-full-pipeline-demo/scripts/verify_report.py`
- **THEN** it SHALL import `FIXED_CAO_BASE_URL` from `houmao.demo.cao_interactive_demo`

#### Scenario: Demo tests patch owning modules directly
- **WHEN** demo unit or integration tests patch non-public helpers or collaborators
- **THEN** they SHALL patch owning submodules such as `houmao.demo.cao_interactive_demo.cao_server`, `houmao.demo.cao_interactive_demo.commands`, `houmao.demo.cao_interactive_demo.runtime`, or `houmao.demo.cao_interactive_demo.cli`
- **AND** they SHALL not target the deleted `houmao.demo.cao_interactive_full_pipeline_demo` module path

### Requirement: Subpackage __init__.py public API re-export

The `cao_interactive_demo/__init__.py` SHALL re-export all public symbols so that `from houmao.demo.cao_interactive_demo import X` works as the canonical new import path.

#### Scenario: Public API importable from subpackage
- **WHEN** a caller uses `from houmao.demo.cao_interactive_demo import start_demo`
- **THEN** the import SHALL succeed and return the `start_demo` function from `commands.py`

#### Scenario: Subpackage __init__.py lists explicit __all__
- **WHEN** the subpackage `__init__.py` is inspected
- **THEN** it SHALL contain an explicit `__all__` list enumerating every re-exported public symbol

### Requirement: Canonical package contract is directly validated

The canonical package surface SHALL be covered by automated tests that import from `houmao.demo.cao_interactive_demo` and verify explicit exports.

#### Scenario: Representative canonical imports are tested
- **WHEN** unit tests run
- **THEN** at least one focused test SHALL import `houmao.demo.cao_interactive_demo`
- **AND** it SHALL verify representative public symbols such as `start_demo` and `FIXED_CAO_BASE_URL`

#### Scenario: Explicit __all__ is tested
- **WHEN** unit tests inspect `houmao.demo.cao_interactive_demo.__all__`
- **THEN** they SHALL verify that expected exported symbols are enumerated
- **AND** those symbols SHALL resolve to the owning module definitions
