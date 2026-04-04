## Why

The current gateway wake-up flow hardcodes notifier prompt text in Python and mixes gateway-operation guidance into transport-specific mailbox skills. That makes mailbox wake-up behavior harder to evolve, and it gives agents only one nominated unread target instead of the unread queue context they need to decide what to inspect first.

## What Changes

- Add a runtime-owned common mailbox skill `houmao-email-via-agent-gateway` that is projected into mailbox-enabled sessions and used directly for gateway-backed mailbox work separately from transport-specific mailbox skills.
- Rename runtime-owned Houmao mailbox skills to the `houmao-<skillname>` convention so projected Houmao-owned skills are clearly distinguished from role-authored or third-party skill names.
- Use the `houmao-<skillname>` naming convention as an explicit invocation boundary so Houmao-owned skills trigger only when the instruction text includes the keyword `houmao`.
- Extend `houmao-mgr agents join` so joined sessions install the Houmao-owned mailbox skills into the adopted tool home by default, with an explicit operator opt-out.
- Update runtime-owned mailbox skill packaging so the common gateway skill projects action-specific subdocuments and curl-first route guidance instead of packing every operation into one long `SKILL.md`.
- Change gateway mail-notifier prompts to summarize all unread message headers found in the current unread snapshot instead of nominating only one target.
- Change notifier prompts to assume the runtime-owned `houmao-email-via-agent-gateway` skill is already installed for the session, direct the agent to use that skill for the current mailbox turn, discover the live gateway endpoint through `pixi run houmao-mgr agents mail resolve-live`, and then use curl against the returned `gateway.base_url`.
- Phrase notifier prompts so the agent is explicitly told to use the Houmao-owned skill by its `houmao-...` name, preserving the required `houmao` keyword that triggers the skill.
- Move the notifier wake-up prompt body into a packaged Markdown template rendered at runtime through string replacement so maintainers can revise prompt wording without editing Python source.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-mailbox-system-skills`: Runtime-owned mailbox skill projection now includes a common gateway-operation skill with action subdocuments and curl-first endpoint guidance, renames projected Houmao-owned mailbox skills to the `houmao-<skillname>` convention, and uses that installed skill as the default attached-session mailbox procedure while transport skills narrow to transport-specific context and fallback behavior.
- `houmao-mgr-agents-join`: Joined-session adoption now installs the Houmao-owned mailbox skill set into the adopted tool home by default so later gateway/mailbox prompts can rely on those installed skills unless the operator explicitly opts out.
- `agent-gateway-mail-notifier`: Gateway notifier prompts now render from a packaged Markdown template, summarize all unread headers in one snapshot, and instruct agents to use the installed `houmao-email-via-agent-gateway` skill together with `houmao-mgr agents mail resolve-live` before choosing what to inspect.

## Impact

- Affected code: `src/houmao/agents/mailbox_runtime_support.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/agents/realm_controller/gateway_service.py`, `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/runtime_artifacts.py`, packaged mailbox skill assets, and new packaged notifier prompt assets.
- Affected tests: gateway notifier prompt tests, mailbox system skill projection tests, and any tests that assert the current single-target notifier wording.
- Affected behavior: mailbox-enabled agents receive a broader runtime-owned skill set, and gateway wake-up prompts become template-driven unread summaries rather than hardcoded single-target task prompts.
