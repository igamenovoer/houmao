## Why

The packaged `houmao-manage-agent-instance` skill is currently described as the canonical Houmao-owned surface for live managed-agent lifecycle work, but it explicitly excludes `houmao-mgr agents relaunch` even though relaunch is a first-class CLI/runtime lifecycle command. That leaves a hole in the packaged skill taxonomy: relaunch is real operator workflow, but no packaged Houmao-owned skill actually owns it.

## What Changes

- Expand the packaged `houmao-manage-agent-instance` skill scope to include managed-agent relaunch alongside launch, join, list, stop, and cleanup.
- Add action-specific relaunch guidance to the packaged skill so it can route both explicit-target relaunch and current-session relaunch through `houmao-mgr agents relaunch`.
- Update the skill's routing and guardrails to distinguish relaunch from fresh launch and to report relaunch-unavailable cases explicitly instead of silently converting them into new-launch advice.
- Update packaged-skill docs/tests that currently describe `relaunch` as out of scope for `houmao-manage-agent-instance`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-manage-agent-instance-skill`: Change the packaged lifecycle-skill requirements so `houmao-manage-agent-instance` covers `agents relaunch`, includes relaunch-specific local guidance, and no longer treats relaunch as out of scope.

## Impact

- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-manage-agent-instance/`
- Likely affected references/tests: packaged system-skill content regression coverage and any docs or references that enumerate the skill's supported lifecycle actions
- No new CLI or runtime relaunch primitive is introduced; this change is about packaged guidance and routing ownership for an existing command
