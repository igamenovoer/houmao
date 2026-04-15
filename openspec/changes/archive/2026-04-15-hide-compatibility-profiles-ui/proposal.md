## Why

`compatibility-profiles/` was retained as optional CAO-facing metadata, but the current Houmao authoring model no longer uses it as a normal project input and CAO compatibility is planned for retirement. Keeping a public bootstrap flag and user documentation for that subtree makes the obsolete path look supported and invites operators to create state that the maintained workflow does not need.

## What Changes

- **BREAKING**: Remove the public `houmao-mgr project init --with-compatibility-profiles` operator surface.
- Stop presenting `.houmao/agents/compatibility-profiles/` as part of the supported project layout in getting-started docs, CLI reference docs, and system-skill guidance.
- Update project-init behavior and tests so ordinary project bootstrap remains focused on `.houmao/`, `catalog.sqlite`, and managed `.houmao/content/` roots, without any compatibility-profile opt-in path.
- Remove `compatibility-profiles/` from the canonical supported tracked agent-definition layout contract.
- Keep internal compatibility-profile-shaped models, launch-scoped projections, and CAO-compatible control-core helpers in source for now where they reduce churn or support the remaining transition path.
- Leave full CAO HTTP/API retirement to a later change; this change only hides/removes the user-facing compatibility-profile authoring surface.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-cli`: remove the public compatibility-profile bootstrap option from project init and make compatibility-profile root creation non-user-facing.
- `docs-getting-started`: remove compatibility-profile authoring/layout guidance from getting-started documentation.
- `docs-cli-reference`: remove compatibility-profile bootstrap and layout guidance from CLI reference documentation.
- `component-agent-construction`: remove `compatibility-profiles/` from the supported canonical tracked agent-definition tree.
- `houmao-project-mgr-skill`: remove project-management skill guidance that asks agents or users to decide whether to pre-create compatibility profiles.

## Impact

- Affected CLI code: `src/houmao/srv_ctrl/commands/project.py`, project-overlay bootstrap tests, and any help/reference generation that captures `project init`.
- Affected docs: `docs/getting-started/quickstart.md`, `docs/getting-started/agent-definitions.md`, `docs/reference/cli/houmao-mgr.md`, and any docs generated from the CLI surface.
- Affected system-skill assets: `src/houmao/agents/assets/system_skills/houmao-project-mgr/`.
- Affected specs: project CLI, getting-started docs, component agent construction, and project-manager skill requirements.
- Internal CAO compatibility code and launch-scoped profile-shaped projections remain available until the broader CAO-retirement change removes or rewrites them.
