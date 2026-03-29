## Why

`houmao-mgr project init` currently creates `.houmao/agents/compatibility-profiles/` even though the directory is optional and not part of the normal project-overlay authoring flow. `houmao-mgr project easy specialist create` also forces operators to provide both an explicit credential name and a system prompt, which makes the higher-level specialist workflow more rigid than the underlying runtime behavior needs.

## What Changes

- Stop generating `.houmao/agents/compatibility-profiles/` during `houmao-mgr project init` by default.
- Add an explicit opt-in path for project init to create `compatibility-profiles/` when an operator specifically wants compatibility metadata roots.
- Make `houmao-mgr project easy specialist create --credential` optional and derive the default credential name as `<specialist-name>-creds`.
- Allow `houmao-mgr project easy specialist create` to omit both `--system-prompt` and `--system-prompt-file`, producing a specialist with no system prompt.
- Treat an empty canonical role prompt as a valid launch input and ensure native prompt-injection paths do not pass empty system-prompt or developer-instructions arguments through to the underlying tool.
- Update project-overlay and quickstart documentation to describe the new default and specialist-authoring behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: ordinary role-backed launches must tolerate intentionally empty role prompts and omit native prompt-injection arguments or bootstrap messages when no prompt content exists.
- `component-agent-construction`: canonical role packages must allow an intentionally empty `system-prompt.md` to represent a role with no system prompt.
- `docs-getting-started`: the documented project-overlay layout and quickstart specialist examples must reflect the new init default, default credential naming, and optional prompt behavior.
- `houmao-mgr-project-cli`: project init must stop creating `compatibility-profiles/` by default and define the explicit opt-in behavior for creating it.
- `houmao-mgr-project-easy-cli`: specialist creation must support default credential naming, reuse-or-overwrite behavior for that derived auth bundle, and promptless specialists.

## Impact

- Affected code: `src/houmao/project/overlay.py`, `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/project/easy.py`, and runtime launch/loading code under `src/houmao/agents/realm_controller/`.
- Affected tests: project command coverage plus runtime launch-plan/backend tests for empty-prompt handling.
- Affected docs: getting-started and CLI reference pages describing project init and project easy specialist authoring.
