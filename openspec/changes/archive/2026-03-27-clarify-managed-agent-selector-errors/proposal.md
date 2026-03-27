## Why

`houmao-mgr` managed-agent commands currently report an infrastructure-style pair-authority connection failure when a local `--agent-name` lookup misses and the default pair authority is unavailable. That hides the more relevant operator problem: the selector did not match any local managed agent, or it matched a tmux/session alias instead of the friendly managed-agent name.

## What Changes

- Clarify `houmao-mgr` selector failure behavior when `--agent-name` does not match a local friendly managed-agent name and remote pair lookup cannot complete.
- Surface local diagnostic hints when the provided `--agent-name` matches a known tmux/session alias but not a published friendly managed-agent name.
- Make single-target managed-agent commands report selector errors in terms of local miss, ambiguity, or remote-unavailable follow-up instead of exposing an unqualified pair-authority connection failure.
- Preserve the current selector contract: `--agent-name` continues to target friendly managed-agent names, and operators are directed toward the correct friendly name or `--agent-id` when a selector is wrong or ambiguous.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: refine managed-agent selector failure reporting so `houmao-mgr` surfaces actionable local miss and alias-hint diagnostics before mentioning remote pair-authority unavailability.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/managed_agents.py`, shared managed-agent selector helpers, and command entrypoints that rely on `resolve_managed_agent_target()`.
- Affected commands: `houmao-mgr agents show/state/prompt/interrupt/stop/relaunch`, explicit-target gateway commands, managed-agent mail commands, and managed-agent turn commands.
- Affected tests: unit coverage for selector resolution and CLI command failures in `tests/unit/srv_ctrl/`.
