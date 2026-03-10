## Context

`src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` is a 2,404-line single-file module implementing the full interactive CAO demo lifecycle: data models, CLI parsing, six lifecycle commands (`start`, `send-turn`, `send-keys`, `inspect`, `verify`, `stop`), CAO server management (launcher config, port scanning, process lifecycle), brain build/session runtime integration, subprocess orchestration, and human/JSON output rendering.

The module is consumed by:
- Unit tests at `tests/unit/demo/test_cao_interactive_full_pipeline_demo.py` (mock paths reference the module by full dotted name)
- Integration tests at `tests/integration/demo/test_cao_interactive_full_pipeline_demo_cli.py`
- Shell scripts at `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh` (invokes via `python -m gig_agents.demo.cao_interactive_full_pipeline_demo`)
- A verification helper at `scripts/demo/cao-interactive-full-pipeline-demo/scripts/verify_report.py` (imports `FIXED_CAO_BASE_URL`)
- README documentation at `scripts/demo/cao-interactive-full-pipeline-demo/README.md`

This change migrates those repository-owned callers to the split package and deletes the legacy module instead of keeping a compatibility shim. That direction matches existing package/export patterns in `src/gig_agents/cao/__init__.py` and `src/gig_agents/agents/brain_launch_runtime/__init__.py`, and it also matches the repo's testing pattern of patching the owning implementation module directly.

## Goals / Non-Goals

**Goals:**
- Split the monolith into a subpackage with 6 focused modules, each targeting roughly a few hundred lines.
- Make `gig_agents.demo.cao_interactive_demo` the canonical import path and `gig_agents.demo.cao_interactive_demo.cli` the CLI module entrypoint.
- Delete `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` after all in-repo callers have been migrated.
- Establish a clean, acyclic internal dependency graph between modules.
- Add direct validation for canonical package imports/exports and migrate demo tests to patch owning submodules.

**Non-Goals:**
- Behavioral changes to any demo command.
- Preserving the legacy module import path or its monkeypatch targets.
- Introducing compatibility wrappers or re-export shims.
- Large logic rewrites beyond extraction and caller migration.

## Decisions

### Decision 1: Subpackage under `src/gig_agents/demo/cao_interactive_demo/`

**Choice**: Create `cao_interactive_demo/` as a Python package (with `__init__.py`) containing the split modules.

**Alternatives considered**:
- *Peer flat files* (`_models.py`, `_cli.py`, etc.) next to the original — rejected because it pollutes the `demo/` namespace and lacks the grouping signal a package provides.
- *Keep the long name* `cao_interactive_full_pipeline_demo/` — rejected for unnecessary verbosity; the shorter name is sufficient given the package context.

### Decision 2: Six-module split by concern

| Module | Responsibility | Approx. lines |
|---|---|---|
| `models.py` | Pydantic models, dataclasses, type aliases, constants | ~280 |
| `cli.py` | `main()`, argparse, CLI resolution helpers | ~175 |
| `commands.py` | Public lifecycle functions: `start_demo`, `send_turn`, `send_control_input`, `inspect_demo`, `verify_demo`, `stop_demo`, plus state I/O helpers | ~380 |
| `cao_server.py` | CAO server ensure/replace/stop, launcher configs, `/proc` TCP port scanning, process lifecycle | ~350 |
| `runtime.py` | Brain build, session start/stop, subprocess runner, tmux cleanup | ~220 |
| `rendering.py` | Human/JSON output rendering, event parsing, JSON I/O, validation helpers, small utilities | ~250 |

**Dependency order** (acyclic):
```
models  ←  rendering  ←  runtime  ←  cao_server  ←  commands  ←  cli
```

The approximate line counts above are design targets, not a normative pass/fail requirement. Cohesion and ownership boundaries matter more than enforcing a hard file-length threshold.

**Alternatives considered**:
- *Fewer modules (3–4)* — rejected; the CAO server management and rendering concerns are large enough to warrant their own homes.
- *More modules (8+)* — rejected; splitting the utility/validation helpers into a separate `_helpers.py` adds indirection for ~50 lines of code.

### Decision 3: Remove the legacy monolith and migrate repository callers

**Choice**: Delete `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` after the split package is wired up, and update repository-owned callers to use the new package or the owning submodules directly.

Migration details:
- `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh` invokes `pixi run python -m gig_agents.demo.cao_interactive_demo.cli`
- `scripts/demo/cao-interactive-full-pipeline-demo/scripts/verify_report.py` imports from `gig_agents.demo.cao_interactive_demo`
- Demo unit/integration tests import public symbols from `gig_agents.demo.cao_interactive_demo` and patch owning modules such as `cao_server`, `commands`, `runtime`, and `cli` directly

**Alternatives considered**:
- *Thin re-export shim* — rejected because it would not preserve the current module-global monkeypatch behavior without extra compatibility plumbing, and that indirection would be less native than simply migrating the tests and scripts.
- *Keep the monolith alongside the package* — rejected because it duplicates ownership, encourages drift, and weakens the signal that the split package is the only supported surface.

### Decision 4: Subpackage `__init__.py` re-exports public API

The `cao_interactive_demo/__init__.py` re-exports the public symbols from the six split modules with an explicit `__all__`. This gives callers a clean canonical import path (`from gig_agents.demo.cao_interactive_demo import ...`) and keeps package-level exports in a single maintained location.

### Decision 5: Direct validation of the canonical package contract

**Choice**: Add focused unit coverage that imports `gig_agents.demo.cao_interactive_demo`, checks representative public symbol identities, and verifies the explicit `__all__`. Existing demo tests are migrated to the new package path, but they are not the only validation mechanism for the package surface.

**Alternative considered**:
- *Rely only on migrated tests and manual inspection* — rejected because the canonical package contract is itself new behavior introduced by this change and deserves direct coverage.

## Risks / Trade-offs

- **Caller migration churn** → Scripts, tests, and README references must be updated atomically with the module split. Mitigation: use repository-wide searches for `cao_interactive_full_pipeline_demo` and include explicit migration tasks for every in-repo caller.
- **Undiscovered out-of-repo callers may break** → Any external consumer still importing `gig_agents.demo.cao_interactive_full_pipeline_demo` will fail after this change. This is accepted because the legacy module is intentionally removed and the demo package is repository-owned.
- **Explicit package exports can drift from owning modules** → `cao_interactive_demo/__init__.py` requires manual maintenance. Mitigation: add focused tests for representative imports and explicit `__all__`.
