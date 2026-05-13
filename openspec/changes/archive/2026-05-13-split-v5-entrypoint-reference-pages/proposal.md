## Why

The `houmao-agent-loop-pairwise-v5` entrypoint has grown into a dense instruction file that mixes activation, routing, generated-contract defaults, runtime model details, and platform-boundary rules. Skill invocation should load only the decision surface needed to choose a route, then let routed pages pull the deeper reference material they need.

## What Changes

- Shorten the top-level `SKILL.md` so it acts as an activation, invariant, operation, and routing index.
- Move reusable detailed guidance from `SKILL.md` into runtime-readable reference pages under the skill package.
- Add a reference-page convention for routed subskills: operation pages list the reference pages they must read before acting.
- Keep maintainer-only rationale in `dev/design/`; do not move runtime guidance there.
- Preserve the current behavior and defaults while changing where guidance lives.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: The skill guidance layout changes so the top-level skill becomes a short router and detailed defaults live in routed reference pages used by authoring and execution subskills.

## Impact

- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`.
- Affected top-level entrypoint: `SKILL.md` becomes shorter and points to subskills/reference pages.
- Affected authoring and execution pages: routed pages gain explicit "read first" references where needed.
- Affected developer design docs: maintain the distinction between runtime reference pages and maintainer-only `dev/design/` notes.
- No expected runtime API, CLI, generated artifact, or dependency change.
