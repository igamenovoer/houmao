## Why

The current gateway mail wake-up contract still exposes internal development-era assumptions to the agent: the notifier prompt precomputes unread email summaries, and the mailbox skills depend on `pixi run houmao-mgr agents mail resolve-live` for ordinary gateway work. That is the wrong boundary for deployed systems, where the gateway should own wake-up and endpoint bootstrap while the agent should discover mailbox state through the gateway API itself.

## What Changes

- Simplify gateway notifier wake-up prompts so they only state that unread mailbox work exists, direct the agent to use `houmao-process-emails-via-gateway`, provide the exact live gateway base URL, and list the full mailbox endpoint URLs for the current round.
- Remove notifier-provided unread email summaries from the wake-up prompt; the agent will list unread mail itself through the shared gateway mailbox API.
- Revise the round-oriented `houmao-process-emails-via-gateway` skill so notifier-driven mailbox rounds are gateway-API-first and do not depend on `pixi` or `houmao-mgr`.
- Revise the lower-level `houmao-email-via-agent-gateway` skill so it no longer assumes notifier-driven invocation: it should use a gateway base URL already present in prompt/context when available, and fall back to `houmao-mgr agents mail resolve-live` only when that URL cannot be determined from context.
- Remove `pixi` references from the agent-visible gateway prompt and mailbox skill surfaces.
- Narrow transport-specific mailbox skills so they reference the revised generic gateway/bootstrap rules instead of duplicating `pixi`-based discovery guidance.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway-mail-notifier`: change the notifier wake-up prompt contract so it no longer embeds unread email summaries or `pixi`-based resolver guidance, and instead bootstraps one gateway-driven mailbox round with the live base URL and endpoint list.
- `agent-mailbox-system-skills`: change the runtime-owned mailbox skill guidance so the round-oriented gateway workflow is API-only, the lower-level gateway skill is context-first with `houmao-mgr` fallback, and agent-visible skill guidance no longer references `pixi`.

## Impact

- Prompt template and notifier prompt renderer in the gateway runtime.
- Runtime-owned mailbox system skill assets for gateway, workflow, and transport-specific guidance.
- Mailbox-related tests covering notifier prompt content, skill projection, and gateway-driven mailbox workflow assumptions.
