## Why

Houmao-owned system skills currently encode family subdirectories like `mailbox/` and `project/` both in the packaged asset tree and, for Codex, in the installed visible path. That no longer matches the native flat skill lookup model used by Claude Code and Gemini CLI, and it turns Codex family nesting into Houmao-specific filesystem structure rather than a real tool contract.

## What Changes

- **BREAKING** Flatten the packaged Houmao-owned system-skill asset tree so each skill lives directly under `src/houmao/agents/assets/system_skills/<skill-name>/` rather than under family subdirectories such as `mailbox/` or `project/`.
- **BREAKING** Flatten the visible installed skill layout so Houmao-owned skills project into each tool's native top-level skill root: `skills/<houmao-skill>/` for Claude and Codex, `.agents/skills/<houmao-skill>/` for Gemini.
- Remove family-derived projection logic from the shared installer and treat grouping only as catalog/set metadata rather than filesystem namespace.
- Add migration behavior so reinstalling into an existing tool home removes previously owned family-namespaced Houmao paths before recording the new flat owned paths.
- Update runtime mailbox skill references, the packaged `houmao-create-specialist` skill, docs, and tests so they describe and assert only the flat native layout.

## Capabilities

### New Capabilities
- `houmao-system-skill-flat-layout`: Define the portable flat packaged and projected layout for Houmao-owned system skills across supported agent tools.

### Modified Capabilities
- `houmao-system-skill-installation`: Change packaged asset paths, Codex-visible projection, and owned-path migration from family-namespaced layout to flat tool-native layout.
- `agent-mailbox-system-skills`: Change Codex mailbox skill discovery from the visible mailbox subtree to top-level Houmao-owned installed skills so mailbox skills follow the same flat native contract as other tools.

## Impact

- Affected code includes [src/houmao/agents/system_skills.py](/data1/huangzhe/code/houmao/src/houmao/agents/system_skills.py), [src/houmao/agents/assets/system_skills/catalog.toml](/data1/huangzhe/code/houmao/src/houmao/agents/assets/system_skills/catalog.toml), mailbox runtime helpers, and the packaged skill asset directories under [src/houmao/agents/assets/system_skills](/data1/huangzhe/code/houmao/src/houmao/agents/assets/system_skills).
- Affected installed-home behavior includes Codex skill paths and Houmao-owned install-state migration for homes that already contain `skills/mailbox/...` or `skills/project/...`.
- Affected docs and tests include the CLI system-skills reference, mailbox/runtime guidance, managed-home assertions, and any OpenSpec change or delta spec that still encodes family-aware skill projection.
