# Tests

Comprehensive test suite organized by purpose.

## Structure

- **unit/** - Fast, deterministic unit tests (pytest/unittest)
- **integration/** - Tests with external services, I/O, or multi-component interactions
- **manual/** - Manually executed scripts (not collected by CI)

## Conventions

- Unit tests: `tests/unit/(subdir)/test_*.py`
- Integration tests: `tests/integration/(subdir)/test_*.py`
- Manual scripts: `tests/manual/manual_*.py`

Prefer `pixi run` for executing tests; keep unit tests hermetic.
