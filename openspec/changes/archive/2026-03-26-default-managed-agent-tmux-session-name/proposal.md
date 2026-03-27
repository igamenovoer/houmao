## Why

The current runtime tmux naming contract derives default session handles from canonical agent identity plus an `agent_id` prefix. That makes default session names harder for operators to predict during interactive `houmao-mgr` use and hides the launch timestamp that is often the most useful discriminator when multiple sessions are created for the same managed agent name.

## What Changes

- Change the default tmux session naming contract for managed tmux-backed launches so the generated handle is `AGENTSYS-<agent_name>-<epoch-ms>` when the caller does not pass an explicit `--session-name`.
- Define the timestamp component as Unix epoch time in milliseconds at launch-time name generation.
- Keep tmux session handles as opaque transport-level labels used only to avoid collisions with unrelated tmux sessions and to make Houmao-owned sessions recognizable to operators.
- Require the default-name generator to fail explicitly if the computed tmux session name is already occupied instead of mutating the candidate name to find a unique suffix.
- Reserve the leading `AGENTSYS<separator>` namespace for system canonicalization so user-provided managed-agent names cannot begin with values such as `AGENTSYS-foo` or `agentsys-foo`.
- Preserve explicit caller-provided `--session-name` behavior as an override; this change applies to the default only.
- Reaffirm that tmux session listing, agent-name-to-tmux-session mapping, and related discovery work continue to flow through the shared registry instead of tmux-name parsing.
- Require user-facing agent targeting by name to use the same raw `--agent-name` value supplied at creation time rather than canonical `AGENTSYS-...` names.
- Update operator-facing documentation and examples to describe the new default naming rule and the explicit conflict failure posture.

## Capabilities

### New Capabilities
<!-- No new capabilities. -->

### Modified Capabilities
- `agent-identity`: Change the default runtime-owned tmux session handle derivation and conflict behavior for tmux-backed managed launches.
- `houmao-mgr-registry-discovery`: Tighten `--agent-name` targeting so operators use the raw creation name and do not pass canonical `AGENTSYS-...` names.

## Impact

- **Code and runtime**: tmux session-name generation and validation in the runtime/controller launch path for tmux-backed managed agents.
- **CLI behavior**: `houmao-mgr agents launch` will produce a different default `tmux_session_name` when `--session-name` is omitted.
- **Input validation**: launch-time managed-agent name validation will reject reserved leading `AGENTSYS<separator>` names supplied by operators.
- **Discovery boundary**: session discovery and agent-to-session mapping continue to rely on shared-registry metadata rather than tmux-name parsing or raw tmux session listing.
- **Targeting UX**: `houmao-mgr agents ... --agent-name` will expect the raw name specified at creation time and reject prefixed canonical forms.
- **Conflict handling**: default naming collisions become explicit launch errors instead of automatic suffix extension.
- **Docs and tests**: runtime identity docs, troubleshooting guidance, and launch-path tests must be updated to the timestamp-based default naming rule.
