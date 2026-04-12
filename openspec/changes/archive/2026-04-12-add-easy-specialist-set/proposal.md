## Why

`houmao-mgr project easy specialist create` can replace an existing specialist, but that is whole-object recreation: omitted optional fields such as skills, prompt posture, model defaults, setup, credential selection, or durable env records are cleared or regenerated. Users need an ordinary edit path for existing specialists so they can change skills and other source-definition fields without removing and recreating the specialist.

## What Changes

- Add `houmao-mgr project easy specialist set --name <specialist> ...` as a patch-style edit command for existing easy specialists.
- Preserve unspecified specialist fields by default, with explicit clear flags for fields that should be removed.
- Support targeted specialist-source edits for prompt content, skill membership, setup, credential display-name selection, prompt mode, model defaults, reasoning level, and durable specialist env records.
- Keep specialist edits catalog-backed and rematerialize the `.houmao/agents/` compatibility projection after successful mutation.
- Keep same-name `project easy specialist create --yes` as the replacement path that may clear omitted optional fields.
- Document the new edit command in the easy-specialists guide, CLI reference, and packaged `houmao-specialist-mgr` system skill guidance.
- Do not change running managed agents in place; specialist edits affect future launches or rebuilds from the reusable specialist source.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: add the patch-style `project easy specialist set` command and define its mutation, preservation, and projection behavior.
- `docs-easy-specialist-guide`: document editing an existing easy specialist without remove/recreate.
- `docs-cli-reference`: document the new `project easy specialist set` command and distinguish patch edits from same-name replacement.
- `houmao-create-specialist-skill`: update the packaged `houmao-specialist-mgr` skill contract so agents can route specialist update requests through the new command.

## Impact

- Affected CLI code: `src/houmao/srv_ctrl/commands/project_easy.py`, shared helpers in `src/houmao/srv_ctrl/commands/project_common.py`, and catalog/projection helpers in `src/houmao/project/catalog.py` as needed.
- Affected tests: unit coverage for `project easy specialist set`, catalog-backed projection updates, preservation semantics, clear flags, and system-skill asset expectations.
- Affected docs and skill assets: `docs/getting-started/easy-specialists.md`, CLI reference pages under `docs/reference/cli/`, and `src/houmao/agents/assets/system_skills/houmao-specialist-mgr/`.
