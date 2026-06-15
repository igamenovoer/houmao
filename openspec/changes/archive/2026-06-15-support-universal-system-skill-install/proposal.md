## Why

Operators need one Houmao-owned system-skill install target that writes to the cross-client Agent Skills convention, `~/.agents/skills`, instead of only to one tool's private home. The existing `kimi` target also needs clearer wording because it means Kimi Code CLI, not the legacy MoonshotAI `kimi-cli` project that upstream says is being wound down in favor of Kimi Code CLI.

## What Changes

- Add a `universal` system-skill install/status/uninstall target that resolves to `~/.agents/skills` by default.
- Keep the Kimi target name as `kimi`; do not add a `kimi-code` selector or alias.
- Update `houmao-mgr system-skills` help, JSON/plain output, and docs so `kimi` is explicitly described as Kimi Code CLI and not legacy `kimi-cli`.
- Correct Kimi discovery guidance so `$KIMI_CODE_HOME/skills` is treated as the Kimi Code user skill root when Kimi is launched with that home, while `universal` remains the cross-client `~/.agents/skills` root.
- Preserve current copy and symlink projection behavior for the new target.

## Capabilities

### New Capabilities

### Modified Capabilities
- `houmao-system-skill-installation`: Extend the shared projection contract to include the `universal` target and clarify Kimi Code projection semantics.
- `houmao-mgr-system-skills-cli`: Extend the operator CLI contract for `--tool universal`, update supported-target help text, and require Kimi help/docs to distinguish Kimi Code CLI from legacy `kimi-cli`.

## Impact

- Affected code:
  - `src/houmao/agents/system_skills.py`
  - `src/houmao/srv_ctrl/commands/system_skills.py`
  - tests for system-skill projection and CLI commands
- Affected docs:
  - `docs/reference/cli/system-skills.md`
  - `docs/reference/cli/houmao-mgr.md`
  - any overview text that enumerates supported system-skill install targets
- No dependency changes are expected.
