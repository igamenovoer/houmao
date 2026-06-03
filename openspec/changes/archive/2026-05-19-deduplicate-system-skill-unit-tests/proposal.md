## Why

The managed system-skill policy change added valuable coverage, but some of that coverage repeats the same assertions through pure helpers, catalog projection, brain construction, and multiple CLI lanes. The resulting unit suite is harder to maintain than the behavior warrants, especially in `tests/unit/srv_ctrl/test_project_commands.py`, where broad end-to-end CLI flows now duplicate lower-level policy and storage tests.

## What Changes

- Refactor managed system-skill unit coverage into a smaller pyramid: exhaustive pure-policy tests, focused storage/projection tests, focused brain-builder integration tests, and thin CLI smoke tests.
- Deduplicate repeated CLI assertions for easy specialists, easy profiles, and explicit launch profiles by keeping one representative happy path per lane and moving shared option validation to helper-level or policy-level tests.
- Reduce filesystem-level assertions in brain-builder tests where equivalent behavior is already covered by `sync_system_skills_for_home` tests, keeping only integration evidence that build inputs are forwarded, resolved, and recorded.
- Keep all user-visible behavior unchanged.
- Preserve verification confidence for parser modes, selector validation, source/profile resolution, managed-home cleanup, project/private skill collision rejection, catalog projection, launch forwarding, and provenance.

## Capabilities

### New Capabilities

- `managed-system-skill-test-coverage`: Defines the expected layered unit-test coverage for managed system-skill policy behavior and the deduplication boundaries between pure logic, storage, runtime integration, and CLI smoke tests.

### Modified Capabilities

None.

## Impact

- Affected tests:
  - `tests/unit/agents/test_system_skills.py`
  - `tests/unit/agents/test_brain_builder.py`
  - `tests/unit/agents/test_definition_parser.py`
  - `tests/unit/project/test_catalog.py`
  - `tests/unit/srv_ctrl/commands/test_agents_core.py`
  - `tests/unit/srv_ctrl/test_project_commands.py`
- Affected implementation code: none expected, except extracting test-only fixtures/helpers if needed.
- Affected docs/API/data formats: none.
- Verification remains `pixi run test`, with focused runs for the touched test modules before the full suite.
