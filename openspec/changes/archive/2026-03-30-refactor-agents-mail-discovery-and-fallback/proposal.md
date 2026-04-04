## Why

The current implementation already improved `houmao-mgr agents mail ...` significantly: pair-backed and manager-owned direct paths now return authoritative results, and local live-TUI fallback is explicitly non-authoritative instead of pretending transcript parsing proves mailbox success. But the agent-facing mailbox workflow is still too contract-heavy for routine turns. Agents still have to rediscover mailbox bindings through a Python module entrypoint, mailbox skills still expose too much filesystem-script detail, and the current CLI shape still lacks an agent-scoped `agents mail resolve-live` discovery path.

This change simplifies the public contract around one agent-scoped surface: `houmao-mgr agents mail`. Agents should resolve live mailbox state through that command family, use gateway HTTP when a live gateway is available, and otherwise use `houmao-mgr` directly without learning transport-local SQLite, lock, or script conventions. The existing authority-aware result contract remains the baseline and should carry forward into the new discovery and fallback workflow.

## What Changes

- **BREAKING** Make `houmao-mgr agents mail ...` the supported agent-scoped mailbox discovery and fallback surface, including a new `resolve-live` command plus current-session targeting when selectors are omitted inside the owning managed tmux session.
- Extend the current authority-aware `houmao-mgr agents mail ...` contract to cover `resolve-live`, `mark-read`, and same-session self-targeting, while preserving the distinction between verified execution and non-authoritative TUI submission fallback.
- Extend verified manager-owned local execution where practical for ordinary mailbox follow-up, especially for new self-targeted workflows, while keeping the existing non-authoritative TUI fallback semantics honest when direct or gateway authority is unavailable.
- Refactor mailbox system skills to use `houmao-mgr agents mail resolve-live`, prefer live gateway HTTP `/v1/mail/*` when available, and fall back to `houmao-mgr agents mail ...` when it is not. When that fallback returns `authoritative: false`, agents must verify outcome through manager-owned or transport-owned state instead of assuming mailbox success from submission alone.
- Simplify the filesystem mailbox public contract so shared `rules/` remains available for markdown policy, formatting, and mailbox-local conventions, while mailbox-owned Python scripts become optional compatibility or implementation detail rather than the ordinary agent workflow contract.
- Update mailbox reference and CLI reference docs to describe the `agents mail resolve-live` and gateway-first workflow and to stop presenting direct `python -m houmao...` discovery as the supported path.
- Absorb and replace the earlier unimplemented `refactor-agent-mailbox-to-houmao-mgr` proposal, which placed current-session mailbox commands under a new top-level `houmao-mgr mail` family instead of under `agents`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: Expand `houmao-mgr agents mail ...` to cover `resolve-live`, `mark-read`, current-session targeting, and the current authority-aware local routing contract.
- `agent-mailbox-system-skills`: Change projected mailbox skills to use `houmao-mgr agents mail resolve-live`, prefer gateway HTTP when available, remove ordinary dependence on direct Python module entrypoints and mailbox-owned scripts, and treat non-authoritative fallback results as requiring verification.
- `agent-mailbox-fs-transport`: Change the filesystem mailbox public contract so `rules/` is policy-oriented guidance and ordinary agent workflows no longer depend on a stable `rules/scripts/` execution protocol.
- `filesystem-mailbox-managed-scripts`: Downgrade runtime-managed helper scripts under `rules/scripts/` to compatibility or implementation detail rather than a required ordinary workflow surface.
- `mailbox-reference-docs`: Update mailbox contract and operations docs to document the new discovery path, gateway-first fallback rule, and rules-as-policy posture.
- `docs-cli-reference`: Update CLI reference coverage for `houmao-mgr agents mail` to include `resolve-live`, `mark-read`, and current-session targeting semantics.

## Impact

- Affected code includes `src/houmao/srv_ctrl/commands/agents/mail.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, `src/houmao/agents/realm_controller/mail_commands.py`, mailbox runtime discovery helpers, direct mailbox execution plumbing, projected mailbox skills, and mailbox documentation.
- The agent-facing mailbox contract changes from "inspect mailbox internals and helper scripts" to "call `houmao-mgr agents mail resolve-live`, then use gateway HTTP or `houmao-mgr agents mail ...`, and verify non-authoritative fallback results explicitly."
- Filesystem mailbox `rules/` remains customizable, but its public role shifts toward markdown policy and formatting guidance instead of executable protocol steps for ordinary mail operations.
