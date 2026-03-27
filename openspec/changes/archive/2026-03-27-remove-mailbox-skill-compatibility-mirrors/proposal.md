## Why

Mailbox skills were originally mirrored under `skills/.system/mailbox/...`, but that hidden location is now known to be a mistake rather than a supported design choice. Keeping both trees doubles the maintained surface, keeps compatibility-only wording alive in prompts and docs, and preserves a misleading contract about where agents should discover mailbox instructions.

## What Changes

- **BREAKING** Stop projecting runtime-owned mailbox skills under `skills/.system/mailbox/...`; mailbox skills SHALL exist only under `skills/mailbox/...`.
- Remove mailbox compatibility-path helpers, prompt text, demo-pack staging logic, and test expectations that mention or depend on `skills/.system/mailbox/...`.
- Update mailbox docs and spec language so the visible `skills/mailbox/...` subtree is the sole mailbox-skill contract rather than a primary-plus-compatibility model.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-mailbox-system-skills`: remove the hidden mailbox compatibility mirror from the mailbox skill projection contract.
- `brain-launch-runtime`: remove hidden mirror references from runtime-owned mailbox prompts and require visible-path-only mailbox prompting.
- `mailbox-reference-docs`: remove compatibility-mirror guidance from mailbox reference and integration documentation.
- `gateway-mail-wakeup-demo-pack`: remove hidden mirror staging and hidden-path references from the provisioned demo workdir contract.

## Impact

- Affected code: `src/houmao/agents/mailbox_runtime_support.py`, `src/houmao/agents/realm_controller/mail_commands.py`, `src/houmao/agents/realm_controller/gateway_service.py`, and `src/houmao/demo/mail_ping_pong_gateway_demo_pack/*`.
- Affected artifacts: mailbox skill projection tests, demo-pack tests, mailbox docs, and fixture role prompts that still mention the hidden path.
- Affected contract surface: any caller, prompt, or demo that still opens `skills/.system/mailbox/...` will need to move to `skills/mailbox/...`.
