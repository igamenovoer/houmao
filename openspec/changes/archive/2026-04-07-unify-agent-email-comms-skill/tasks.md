## 1. Reshape the mailbox skill assets

- [x] 1.1 Create the `src/houmao/agents/assets/system_skills/houmao-agent-email-comms/` skill package with a unified `SKILL.md`, ordinary mailbox action pages, transport-specific subpages, shared references, and agent metadata.
- [x] 1.2 Update `src/houmao/agents/assets/system_skills/houmao-process-emails-via-gateway/` so its workflow guidance points to `houmao-agent-email-comms` for ordinary mailbox operations inside a processing round.
- [x] 1.3 Update `src/houmao/agents/assets/system_skills/houmao-agent-messaging/` mailbox guidance to delegate ordinary mailbox actions and transport-local questions to `houmao-agent-email-comms`, then remove the legacy top-level ordinary mailbox skill packages.

## 2. Update runtime-owned mailbox skill projection and inventory

- [x] 2.1 Update `src/houmao/agents/assets/system_skills/catalog.toml` so the current mailbox inventory surfaces `houmao-agent-email-comms` and no longer surfaces `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, or `houmao-email-via-stalwart`.
- [x] 2.2 Update `src/houmao/agents/mailbox_runtime_support.py` to project and advertise the two-skill mailbox surface built from `houmao-process-emails-via-gateway` and `houmao-agent-email-comms`.
- [x] 2.3 Update any manager- or gateway-owned mailbox guidance emitters that reference installed mailbox skill names so they advertise `houmao-agent-email-comms` consistently.

## 3. Align prompts, notifier copy, and related runtime messaging

- [x] 3.1 Update notifier wake-up prompt generation in `src/houmao/agents/realm_controller/gateway_service.py` so supporting-material guidance references `houmao-agent-email-comms` as the lower-level operational skill.
- [x] 3.2 Update mailbox help or fallback guidance in `src/houmao/agents/realm_controller/mail_commands.py` and any related runtime prompt copy to use the unified mailbox skill surface.
- [x] 3.3 Search runtime-owned assets and demo prompt text for references to the removed legacy mailbox skill names and replace them with the new unified routing contract where appropriate.

## 4. Refresh tests and validate the new mailbox skill surface

- [x] 4.1 Update unit tests that assert packaged skill names, install sets, projected skill paths, or mailbox prompt copy to expect `houmao-agent-email-comms`.
- [x] 4.2 Update integration tests or demo-contract assertions that check visible mailbox skill projection or notifier guidance to match the unified mailbox skill surface.
- [x] 4.3 Run targeted validation for the changed mailbox skill assets, system-skill installer behavior, and mailbox notifier or prompt-generation paths.
