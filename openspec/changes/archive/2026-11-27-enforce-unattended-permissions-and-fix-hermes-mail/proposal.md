# Proposal

## Why

Houmao currently treats `unattended` as permission defaults that an authored setting can override. Hermes also ignores the mode when configuring native command approvals and declines ACP file edits, which stalled the Stalwart round trip in [issue #105](https://github.com/igamenovoer/houmao/issues/105).

## What Changes

- **BREAKING** Make `unattended` select the maximum qualified native permissions without operator approval waits for every supported managed provider and run mode. Reject conflicting approval or sandbox inputs before starting or replacing an agent. Use `as_is` for custom permission settings.
- Apply the Hermes posture at launch and explicit relaunch. Use the broadest qualified native ACP edit mode and answer attributable tool-permission requests with an advertised one-time grant. Expose a safe pending-approval indicator for manual Hermes TUI sessions.
- Return schema-based HTTP 422 guidance for offline and online mail-list requests. Keep request values and arbitrary key names private.
- Give Hermes the public mail skill lookup and the correct entrypoint route for notifier rounds and ordinary mail. Preserve verified self, binding checks, and the protected child layout.
- Qualify the effective posture across all supported provider and mode combinations. Re-run Hermes structured file writes and the live Stalwart round trip without operator intervention.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `versioned-launch-policy-registry` defines the qualified maximum unattended posture for each provider and backend.
- `brain-launch-runtime` applies and verifies that posture before fresh start and explicit relaunch.
- `recipe-launch-overrides` checks authored permission settings against the selected posture while resolving launch inputs.
- `kimi-code-tui-support` specifies native `auto` for unattended TUI start and resume.
- `houmao-mgr-project-easy-cli` applies the same launch validation to Easy instances.
- `docs-launch-policy-reference` documents maximum permission, conflicting settings, and the move to `as_is` for custom permissions.
- `docs-run-phase-reference` documents native Kimi posture and continuation.
- `hermes-agent-runtime` specifies native approval policy, ACP tool permissions, and TUI approval observation.
- `test-agent-launch-fixtures` qualifies managed Hermes permission and observation behavior.
- `agent-gateway` specifies safe public mail-list validation guidance.
- `agent-gateway-mail-notifier` sends Hermes through its public agent entrypoint with the current mailbox context.
- `agent-mailbox-system-skills` aligns mailbox routing with the installed public roots and protected children.
- `houmao-parent-scoped-skill-entrypoints` specifies how Hermes loads the selected child through its verified public route.
- `docs-gateway-mail-notifier-reference` describes Hermes public-skill lookup and binding context.

## Impact

This changes shared launch-policy resolution, provider configuration, Hermes TUI state and ACP handling, mail-list error responses, installed skill instructions, and qualification fixtures. Omitted prompt mode still selects `unattended`. Profiles that intentionally choose a lower permission posture must select `as_is`. Provider hard denials, execution-owner boundaries, and Houmao gateway authorization still apply.
