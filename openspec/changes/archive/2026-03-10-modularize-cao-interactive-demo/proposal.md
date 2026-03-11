## Why

`src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` is a 2,404-line monolith containing at least six orthogonal concerns (data models, CLI parsing, demo lifecycle commands, CAO server management, brain/session runtime, and output rendering/utilities). This makes the file difficult to navigate, reason about, and test in isolation. Breaking it into a focused subpackage improves cognitive load, enables per-concern unit testing, and aligns with the project's pattern of small, typed, single-responsibility modules.

## What Changes

- Extract a new `cao_interactive_demo/` subpackage under `src/gig_agents/demo/` with focused modules: `models.py`, `cli.py`, `commands.py`, `cao_server.py`, `runtime.py`, and `rendering.py`.
- Remove `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` after the split package is in place instead of keeping a backward-compatibility shim.
- Migrate repository-owned callers (demo unit/integration tests, shell scripts, verification helpers, and README references) to `gig_agents.demo.cao_interactive_demo` or the owning submodules.
- Add direct validation for the canonical package contract, including representative imports from `gig_agents.demo.cao_interactive_demo` and explicit `__all__` coverage.

## Capabilities

### New Capabilities

- `cao-interactive-demo-module-structure`: Defines the subpackage layout, module responsibilities, internal dependency ordering (models → rendering → runtime → cao_server → commands → cli), the canonical package import path, and the removal of the legacy monolith after in-repo callers are migrated.

### Modified Capabilities

_(none)_

## Impact

- **Code**: `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` is deleted after the new `src/gig_agents/demo/cao_interactive_demo/` subpackage is in place.
- **Tests**: Demo unit/integration coverage migrates to `gig_agents.demo.cao_interactive_demo` and its owning submodules, and the change adds focused coverage for canonical exports and `__all__`.
- **Scripts**: `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh`, `scripts/demo/cao-interactive-full-pipeline-demo/scripts/verify_report.py`, and related README references are updated to use the split package.
- **Dependencies**: No new external dependencies. Internal imports within the new subpackage use the existing `gig_agents.agents` and `gig_agents.cao` packages.
- **APIs**: The supported import surface becomes `gig_agents.demo.cao_interactive_demo`; the legacy monolith path is removed.
