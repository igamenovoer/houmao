## Why

`project easy profile ...` and `project agents launch-profiles ...` are documented as two user-facing lanes over one shared catalog-backed launch-profile family, but the current CLI enforces that split inconsistently. Today `project agents launch-profiles list` hides easy profiles while `get` can still read them, and both remove surfaces can delete the other lane by name, which makes the operator experience look like partial discovery bugs instead of deliberate lane ownership.

## What Changes

- Make launch-profile lane ownership consistent across `list`, `get`, `set`, and `remove` for both the explicit and easy profile command families.
- Add operator-facing wrong-lane errors that explain which lane the named profile belongs to and direct the operator to the correct command family.
- Improve empty-list behavior so a lane that has no local results can surface a note when profiles exist only in the other lane instead of silently returning an empty list with no guidance.
- Update launch-profile documentation to explain that both lanes share storage and projection paths while still remaining lane-bounded management surfaces.
- **BREAKING**: wrong-lane `get` and `remove` flows that currently succeed by name will fail with redirect guidance instead of reading or deleting the other lane's profile.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-agents-launch-profiles`: tighten explicit launch-profile lane enforcement for `get` and `remove`, and clarify empty-list results when only easy profiles exist.
- `houmao-mgr-project-easy-cli`: tighten easy-profile lane enforcement for `remove`, and clarify empty-list results when only explicit launch profiles exist.
- `docs-launch-profiles-guide`: document the lane-bounded management model more explicitly, including shared storage, command ownership, and wrong-lane operator guidance.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/project_common.py`, `src/houmao/srv_ctrl/commands/project_launch_profiles.py`, `src/houmao/srv_ctrl/commands/project_easy.py`, and the easy-profile helper path in `src/houmao/project/easy.py`.
- Affected tests: `tests/unit/srv_ctrl/test_project_commands.py` needs regression coverage for wrong-lane `get`, wrong-lane `remove`, and lane-aware empty-list guidance.
- Affected docs: `docs/getting-started/launch-profiles.md` and any nearby getting-started references that currently imply the shared path without making lane ownership explicit.
- No catalog schema or projection-layout change is expected; this is a CLI contract and documentation consistency fix over the existing shared launch-profile model.
