## Why

Easy profiles currently have create/list/get/remove commands but no patch command, so changing a stored default requires manually removing and recreating the profile. Explicit launch profiles already have `set`, but same-name recreation still fails instead of offering a deliberate replacement path, which makes full replacement workflows awkward for both profile lanes.

## What Changes

- Add a patch-style `houmao-mgr project easy profile set --name <profile> ...` command that mirrors the existing explicit `project agents launch-profiles set` field behavior and clear flags while preserving unspecified stored fields.
- Add deliberate same-lane replacement for profile creation: `project easy profile create --name <profile> ... --yes` and `project agents launch-profiles add --name <profile> ... --yes` replace an existing profile in the same lane.
- Reject cross-lane replacement so easy-profile creation cannot replace an explicit launch profile and explicit launch-profile creation cannot replace an easy profile.
- Keep direct launch-time overrides runtime-only; editing commands mutate only the stored reusable profile and rematerialize the compatibility projection for future launches.
- Update CLI reference, easy-profile guide, launch-profile guide, and relevant Houmao system-skill routing docs so operators and agents discover `set` and deliberate replacement.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-launch-profiles`: Define shared launch-profile mutation semantics, including patch versus same-lane replacement and no live-instance mutation.
- `houmao-mgr-project-easy-cli`: Add `project easy profile set` and same-lane `profile create --yes` replacement behavior.
- `houmao-mgr-project-agents-launch-profiles`: Add same-lane `launch-profiles add --yes` replacement behavior while preserving the existing `set` patch contract.
- `docs-cli-reference`: Document the new easy-profile `set` command and same-lane replacement confirmation on both profile authoring lanes.
- `docs-easy-specialist-guide`: Document editing and replacement for specialist-backed easy profiles.
- `docs-launch-profiles-guide`: Document the conceptual difference between direct launch overrides, patching a reusable profile, and replacing a reusable profile.
- `houmao-create-specialist-skill`: Update `houmao-specialist-mgr` guidance to route easy-profile edit requests through `project easy profile set` and deliberate replacement through `create --yes`.
- `houmao-project-mgr-skill`: Update explicit launch-profile management guidance to include same-lane replacement through `launch-profiles add --yes`.

## Impact

- CLI code in `src/houmao/srv_ctrl/commands/project.py` for easy-profile command registration, create-time conflict handling, and explicit launch-profile add replacement.
- Shared catalog/profile storage behavior through the existing launch-profile upsert path in `src/houmao/project/catalog.py`, with lane checks in the CLI layer.
- Unit tests in `tests/unit/srv_ctrl/test_project_commands.py` for easy-profile patching, same-lane replacement, cross-lane conflict rejection, and compatibility projection refresh.
- Documentation under `docs/reference/cli/houmao-mgr.md`, `docs/getting-started/easy-specialists.md`, and `docs/getting-started/launch-profiles.md`.
- System-skill assets for `houmao-specialist-mgr` and `houmao-project-mgr`.
