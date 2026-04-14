## Why

The mailbox lifecycle now separates `read` from work completion, but notifier configuration still has only one behavior shape. Operators need the default notifier to wake on any unarchived inbox mail while still having an explicit lower-noise mode that wakes only for unread inbox mail.

## What Changes

- Add a mail-notifier notification mode with allowed values `any_inbox` and `unread_only`.
- Default notifier enablement to `any_inbox`, meaning any unarchived mail in the inbox remains notification-eligible regardless of `read` or `answered` state.
- Add opt-in `unread_only` mode, meaning only unread unarchived inbox mail is notification-eligible.
- Persist and report the selected notifier mode in gateway notifier status, direct gateway HTTP, and managed-agent gateway proxy responses.
- Add CLI support for configuring notifier mode through `houmao-mgr agents gateway mail-notifier enable`.
- Update notifier prompts and runtime-owned mailbox skills so the agent understands the triggering mode while still treating archive as the completion action.
- Update gateway notifier and CLI reference docs to replace stale unread-as-completion wording with the new mode-aware workflow.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-gateway-mail-notifier`: add mode-aware notifier configuration, polling, status, and prompt semantics.
- `houmao-srv-ctrl-native-cli`: expose notifier mode configuration on the native `agents gateway mail-notifier enable` command.
- `passive-server-gateway-proxy`: preserve notifier mode through managed-agent gateway mail-notifier proxy routes.
- `agent-mailbox-system-skills`: make notifier-driven processing guidance mode-aware while preserving archive-as-completion semantics.
- `houmao-agent-gateway-skill`: document open-inbox default and the `unread_only` notifier mode in gateway skill guidance.
- `docs-cli-reference`: document the notifier mode CLI option and default.
- `docs-gateway-mail-notifier-reference`: document mode-aware notifier behavior, status, prompt wording, and archive completion.

## Impact

- Gateway notifier models, durable storage, polling logic, prompt rendering, and tests under `src/houmao/agents/realm_controller/`.
- Server, passive-server, and client models that proxy `GatewayMailNotifierPutV1` and `GatewayMailNotifierStatusV1`.
- Native `houmao-mgr agents gateway mail-notifier enable` CLI implementation and related tests.
- Runtime-owned system skill assets for gateway notifier control and gateway-notified email processing.
- Reference docs for gateway mail-notifier behavior and the `agents gateway` CLI surface.
