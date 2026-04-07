## Why

The current Houmao packaged skill boundary makes `houmao-manage-specialist` stop at specialist definition CRUD even though operators naturally think of launching and stopping a specialist-backed instance as part of the same easy-specialist workflow. That split is defensible internally, but it creates avoidable routing friction for agents and users working from the specialist mental model.

## What Changes

- Expand `houmao-manage-specialist` so it can route specialist-scoped `launch` and `stop` actions in addition to `create`, `list`, `get`, and `remove`.
- Require the specialist skill to tell the user that additional live-agent lifecycle management should continue through `houmao-manage-agent-instance` after a specialist-backed launch or stop flow.
- Update `houmao-manage-agent-instance` so its documented boundary remains canonical for general live-agent lifecycle while no longer assuming that specialist-backed launch and stop can originate only there.
- Update system-skill documentation so the two Houmao-owned skills are described as overlapping intentionally at the specialist workflow entry point rather than as strictly disjoint surfaces.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-create-specialist-skill`: expand the packaged specialist-management skill contract to include specialist-scoped launch and stop plus mandatory post-action handoff guidance to `houmao-manage-agent-instance`.
- `houmao-manage-agent-instance-skill`: adjust the lifecycle skill boundary so it remains the canonical live-instance workflow without requiring exclusive ownership of specialist-backed launch and stop entry.
- `docs-cli-reference`: update `docs/reference/cli/system-skills.md` to describe the revised relationship between `houmao-manage-specialist` and `houmao-manage-agent-instance`.
- `docs-readme-system-skills`: update the README system-skills summary so `houmao-manage-specialist` is no longer described as CRUD-only.

## Impact

- Affected packaged skill assets under `src/houmao/agents/assets/system_skills/houmao-manage-specialist/` and `src/houmao/agents/assets/system_skills/houmao-manage-agent-instance/`
- Affected OpenSpec contracts for both system skills and their documentation
- Affected system-skill docs in `docs/reference/cli/system-skills.md` and `README.md`
