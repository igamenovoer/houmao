## Why

Kimi Code now has a documented `kimi login` device-code OAuth command, and agents need guidance for using it safely with Houmao credential storage. The current credential-manager skill only tells agents that Kimi has no maintained Houmao login helper, so it cannot help users through the supported Kimi Code login path even though Houmao can already import a Kimi Code home through `--code-home`.

## What Changes

- Add Kimi Code login-handling guidance to `houmao-credential-mgr` as a Kimi-specific subskill or action branch.
- Teach agents to run `kimi login` in a dedicated tmux session with an isolated `KIMI_CODE_HOME`, forwarding the same proxy variables used by other login guidance.
- Teach agents to import the resulting default Kimi Code home through existing `project credentials kimi add|set --code-home <dir>` or the direct native-agent equivalent.
- Keep Kimi out of the maintained `credentials <tool> login` helper list; this change documents a lower-level Kimi recovery/import workflow, not a new `houmao-mgr credentials kimi login` command.
- Update Kimi credential-kind guidance and packaged skill tests so the new Kimi login path is discoverable without implying that arbitrary Kimi homes or scoped OAuth files are fully supported.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-manage-credentials-skill`: add requirements for Kimi Code login-handling guidance that uses `kimi login`, isolated `KIMI_CODE_HOME`, tmux/proxy preservation, and existing Kimi credential import flags while preserving the no-maintained-helper boundary.

## Impact

- Affected packaged skill assets under `src/houmao/agents/assets/system_skills/houmao-credential-mgr/`, especially `SKILL.md`, `actions/login.md`, `references/kimi-credential-kinds.md`, and the new Kimi login-handling subskill or action page.
- No expected new `houmao-mgr project credentials kimi login` or internal native-agent Kimi login command.
- Test impact is packaged system-skill text coverage for Kimi login handling, Kimi CRUD/import guidance, and relative links.
