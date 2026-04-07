## Why

Houmao's basic email-operation guidance is currently split across `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, and `houmao-email-via-stalwart`, even though those skills share the same routing spine and mostly differ only in supporting details. That fragmentation makes mailbox behavior harder to discover, harder to route from other skills, and more expensive to evolve because every operational change must be repeated across multiple top-level skill packages.

We now want one Houmao-owned email communication skill that covers ordinary mailbox operations in one place while keeping `houmao-process-emails-via-gateway` separate as the round-oriented workflow skill. This lets operators and agents discover one basic email skill, while transport-specific or gateway-specific cases move into subpages instead of separate installed skills.

## What Changes

- Introduce a new runtime-owned Houmao skill `houmao-agent-email-comms` as the single installed entrypoint for ordinary email communication work.
- Move shared mailbox operations such as `resolve-live`, `status`, `check`, `read`, `send`, `reply`, and `mark-read` under `houmao-agent-email-comms` action pages.
- Move filesystem-specific and Stalwart-specific guidance under `houmao-agent-email-comms` subpages or references instead of separate top-level installed skills.
- Keep `houmao-process-emails-via-gateway` as a separate installed skill for notifier-driven round processing, and update it to point to `houmao-agent-email-comms` when the round needs ordinary mailbox operations.
- Update `houmao-agent-messaging` mailbox delegation so generic mailbox routing hands off to `houmao-agent-email-comms` for basic email operations and to `houmao-process-emails-via-gateway` for notifier rounds.
- **BREAKING** Replace the projected and installable top-level skill names `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, and `houmao-email-via-stalwart` with `houmao-agent-email-comms`.
- **BREAKING** Update the packaged mailbox skill catalog, install sets, and runtime prompts so mailbox-enabled sessions project and advertise `houmao-agent-email-comms` instead of the removed top-level basic email skills.

## Capabilities

### New Capabilities

- `houmao-agent-email-comms-skill`: Defines the contract for the unified Houmao-owned basic email communication skill, including shared mailbox operations, transport-aware routing, and internal subpage structure.

### Modified Capabilities

- `agent-mailbox-system-skills`: Changes the runtime-projected mailbox skill set and mailbox-skill guidance to use `houmao-agent-email-comms` plus the separate round workflow skill.
- `houmao-agent-messaging-skill`: Changes mailbox delegation from the three legacy basic email skills to `houmao-agent-email-comms`, while preserving delegation to `houmao-process-emails-via-gateway` for workflow rounds.
- `houmao-mgr-system-skills-cli`: Changes the packaged installable mailbox skill inventory, named mailbox sets, and install/status reporting to surface `houmao-agent-email-comms` instead of the removed legacy skills.
- `agent-gateway-mail-notifier`: Changes notifier prompt supporting-material guidance so round prompts and related mailbox instructions reference `houmao-agent-email-comms` as the lower-level operational skill for ordinary mailbox actions.

## Impact

- Affected assets under `src/houmao/agents/assets/system_skills/`, especially mailbox skill packages and `houmao-agent-messaging`.
- Affected runtime mailbox-skill projection and naming logic in `src/houmao/agents/mailbox_runtime_support.py`.
- Affected packaged system-skill inventory in `src/houmao/agents/assets/system_skills/catalog.toml`.
- Affected notifier and mailbox prompt rendering in `src/houmao/agents/realm_controller/gateway_service.py` and `src/houmao/agents/realm_controller/mail_commands.py`.
- Affected unit and integration tests that assert installed skill names, projected paths, or mailbox prompt copy.
