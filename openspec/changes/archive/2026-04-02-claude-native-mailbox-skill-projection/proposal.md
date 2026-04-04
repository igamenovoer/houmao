## Why

Claude Code does not discover Houmao mailbox skills natively in the current runtime layout because Houmao projects them under `skills/mailbox/<skill>/SKILL.md` instead of a Claude-native top-level skill directory. This blocks `/skills` and `/<skill-name>` discovery for mailbox workflows in live Claude TUI sessions even though the skill files are present.

## What Changes

- Modify Claude mailbox-skill projection so runtime-owned Houmao mailbox skills install as top-level native Claude skills under the Claude home skill root instead of under the `mailbox/` namespace subtree.
- Keep `CLAUDE_CONFIG_DIR` as a Houmao-owned isolated runtime home rather than reusing `<workdir>/.claude` from the launched project.
- Keep mailbox skill path resolution, prompt construction, and runtime docs tool-aware so Claude uses native top-level skill paths while other tools can retain their existing discoverable mailbox layout.
- Update runtime prompts, docs, demo expectations, and tests to validate Claude-native mailbox skill discovery and invocation behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-mailbox-system-skills`: Change the mailbox system-skill projection contract so Claude sessions use native top-level Houmao skill directories instead of `skills/mailbox/...`.
- `brain-launch-runtime`: Change runtime mailbox-skill projection and prompt path assumptions so launched Claude sessions expose mailbox skills through Claude-native discoverable paths.
- `mailbox-reference-docs`: Update mailbox reference and internals documentation to describe tool-specific mailbox skill projection, including Claude-native top-level skill paths.

## Impact

- Affected code: `src/houmao/agents/mailbox_runtime_support.py`, runtime prompt/path helpers, Claude-oriented launch/build assets, mailbox docs, and focused runtime/demo tests.
- Affected behavior: Claude TUI sessions should see Houmao mailbox skills through `/skills` and `/<skill-name>` without requiring direct file-path fallback for native invocation.
- Affected behavior: Houmao should not populate the user repo's `.claude/` directory with runtime-owned Claude state just to make mailbox skills discoverable.
- Affected demos: Claude-backed mailbox demos, including `scripts/demo/single-agent-mail-wakeup`, should rely on native Claude mailbox skill discovery after reprojection/restart.
