## Why

Managed agents now have a durable `houmao-memo.md`, but the launch prompt does not explicitly remind each agent to consult that memo on every prompt turn. Agents also lack a compact packaged Houmao-owned skill that routes memo and memory-page editing requests to the maintained `houmao-mgr agents memory ...` surface.

## What Changes

- Add a default-enabled managed prompt-header section named `memo-cue` that renders as `<memo_cue>`.
- Render `memo-cue` with the resolved absolute path to the current managed agent's `houmao-memo.md` at launch time.
- Tell the agent to read that memo at the start of each prompt turn before planning or acting, and to follow relevant authored links into `pages/` when needed.
- Add a packaged system skill named `houmao-memory-mgr` for reading, editing, appending, pruning, and organizing the managed memo and contained `pages/` files.
- Add a dedicated system-skill set for managed memory guidance and include it in managed launch, managed join, and CLI-default system-skill selections.
- Update managed-memory, system-skills, CLI, and docs contracts so the new prompt section and skill are visible and controllable.

## Capabilities

### New Capabilities
- `houmao-memory-mgr-skill`: packaged Houmao-owned skill for managed-agent memo and memory-page editing through the supported memory surfaces.

### Modified Capabilities
- `managed-launch-prompt-header`: add the default-enabled `memo-cue` section, its render order, path-specific prompt content, section-policy behavior, and metadata/layout expectations.
- `agent-memory-pages`: clarify that managed launches cue agents to use the fixed memo as per-turn durable context and to treat `pages/` as linked supporting material rather than generated indexes.
- `houmao-system-skill-installation`: add `houmao-memory-mgr` to the packaged skill inventory and fixed install selections through a dedicated managed-memory set.
- `houmao-mgr-system-skills-cli`: list/install/status output must surface the new skill and set in current inventory and default selections.
- `docs-managed-launch-prompt-header-reference`: document the new `memo-cue` section, default policy, render order, and absolute memo path behavior.
- `docs-system-skills-overview-guide`: document the new memory-management skill and its relationship to managed launch/join auto-install.
- `docs-getting-started`: update managed-memory user guidance to explain the per-turn memo cue and the new packaged skill.

## Impact

- Affected prompt composition code and tests around `src/houmao/agents/managed_prompt_header.py`.
- Affected managed launch and relaunch call sites that compose the effective prompt after resolving `AgentMemoryPaths`.
- Affected packaged skill assets and catalog under `src/houmao/agents/assets/system_skills/`.
- Affected `houmao-mgr system-skills list|install|status` expectations and tests.
- Affected managed-memory and system-skill documentation.
- No new memory storage layout or runtime state database is introduced; the change uses the existing `houmao-memo.md`, `pages/`, gateway, pair-server, and CLI memory operations.
