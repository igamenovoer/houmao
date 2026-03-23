## Why

The runtime now mirrors mailbox system skills into visible `skills/mailbox/...` paths so Codex can discover them safely, but the generic runtime `mail` prompt, tests, and mailbox docs still treat hidden `.system/mailbox/...` paths as the primary contract. That leaves one real runtime bug in place for non-demo `mail` flows and keeps the documented mailbox-skill contract out of sync with the actual discovery behavior across Codex and Claude homes.

## What Changes

- Make the visible `skills/mailbox/...` projection the primary runtime-owned mailbox skill surface for mailbox-enabled homes, while keeping `skills/.system/mailbox/...` only as a compatibility mirror.
- Update runtime `mail` prompt construction so mailbox-enabled sessions are pointed at a discoverable mailbox skill surface instead of the hidden `.system/mailbox/...` reference.
- Tighten the runtime mailbox prompt and skill contract so tool-specific discovery expectations stay explicit: Codex-compatible prompting must not rely on hidden-dot skill discovery, while Claude-compatible homes continue to resolve the same projected skills from `<config-home>/skills`.
- Refresh mailbox reference docs and focused tests so they describe and verify the visible mailbox skill surface instead of the hidden cache-style path as the normative contract.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-mailbox-system-skills`: change the runtime-owned mailbox skill projection contract so the visible `skills/mailbox/...` projection is the primary discoverable surface and hidden `.system` copies are compatibility mirrors rather than the normative mailbox skill namespace.
- `brain-launch-runtime`: change the runtime `mail` prompt contract so prompt construction points agents at a discoverable projected mailbox skill surface instead of the hidden `.system/mailbox/...` path.
- `mailbox-reference-docs`: change the mailbox reference contract so docs explain the visible mailbox skill projection and tool-usable discovery path rather than documenting `.system/mailbox/...` as the main runtime path.

## Impact

- Affected code:
  - `src/houmao/agents/mailbox_runtime_support.py`
  - `src/houmao/agents/realm_controller/mail_commands.py`
  - `src/houmao/agents/brain_builder.py`
  - focused mailbox and brain-builder tests
- Affected docs:
  - `docs/reference/mailbox/quickstart.md`
  - `docs/reference/mailbox/contracts/runtime-contracts.md`
  - `docs/reference/mailbox/internals/runtime-integration.md`
- Affected systems:
  - mailbox-enabled Codex homes
  - mailbox-enabled Claude homes
  - runtime-owned `mail check` / `mail send` / `mail reply` prompt construction
