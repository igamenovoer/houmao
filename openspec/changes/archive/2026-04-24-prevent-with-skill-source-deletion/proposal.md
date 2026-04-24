## Why

`houmao-mgr project easy specialist create|set --with-skill <dir>` currently has a safety hole where re-registering a skill can delete or consume caller-owned source content instead of mutating only Houmao-managed overlay paths. This is dangerous data loss behavior, so the project needs an explicit contract that source paths provided by operators are read-only inputs to skill registration.

## What Changes

- Tighten project skill registration so `--with-skill` and `project skills add|set` never delete, move, or rewrite caller-owned source directories.
- Define a hard ownership boundary: only Houmao-managed canonical content and derived projection paths under the project overlay may be mutated during skill registration, refresh, rollback, or failure handling.
- Require destructive replacement logic to operate on unresolved Houmao-owned paths rather than resolved user-owned targets when canonical entries currently use symlinks.
- Require failure handling for `--with-skill` and project skill registration to leave caller-owned sources untouched, even when part of the command has already mutated Houmao-managed content.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: change `--with-skill` so specialist create/set treat the provided source directory as read-only input and never mutate caller-owned content.
- `houmao-mgr-project-skills-cli`: change project skill add/set semantics so registration may update Houmao-managed canonical/projection paths but must never delete or rewrite the operator-provided source path, including when the canonical entry is symlink-backed.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/project_easy.py`, `src/houmao/srv_ctrl/commands/project_skills.py`, and `src/houmao/project/catalog.py`
- Affected systems: project skill registry under `.houmao/content/skills/`, derived `.houmao/agents/skills/` projection, and easy-specialist skill binding flows
- Validation impact: add regression coverage for re-registering symlink-backed canonical skills through `--with-skill` and `project skills set`
