## Context

The current gateway mail notifier and mailbox skill stack was shaped by development-time ergonomics rather than deployed-runtime boundaries. The notifier prompt currently serializes unread email summaries into the prompt, and the projected mailbox skills still direct agents to `pixi run houmao-mgr agents mail resolve-live` for ordinary gateway mailbox work.

That coupling causes two problems:

1. the notifier prompt is doing mailbox listing work that the gateway API already supports through `POST /v1/mail/check`, and
2. the agent-visible gateway workflow depends on a development launcher (`pixi`) that will not be present in deployed environments.

At the same time, not every use of `houmao-email-via-agent-gateway` is notifier-driven. Some ad hoc mailbox tasks still need a generic way to discover the current gateway base URL when the prompt does not already provide it.

## Goals / Non-Goals

**Goals:**

- make notifier-driven mailbox rounds gateway-API-first from the agent’s point of view
- remove unread email summary rendering from the notifier prompt
- remove `pixi` from agent-visible gateway prompt and mailbox skill guidance
- keep `houmao-process-emails-via-gateway` strict for notifier rounds: it should assume the current round already provides the live gateway base URL
- keep `houmao-email-via-agent-gateway` usable outside notifier rounds by allowing context-first gateway URL discovery with `houmao-mgr agents mail resolve-live` as fallback
- keep transport-specific skills aligned with the revised bootstrap rules instead of duplicating legacy resolver wording

**Non-Goals:**

- changing the gateway’s internal unread-mail polling or reminder scheduling logic
- introducing a new mailbox transport or changing mailbox authority semantics
- redesigning the shared `/v1/mail/*` route set for this change
- removing `houmao-mgr agents mail resolve-live` from all workflows; it remains the generic fallback when context does not provide the gateway URL

## Decisions

### 1. Make notifier wake-up prompts presence-based, not snapshot-based

The notifier prompt will no longer embed unread email summaries. It will only say that unread shared-mailbox work exists, tell the agent to use `houmao-process-emails-via-gateway`, provide the exact live gateway base URL for the current round, and list the full mailbox endpoint URLs for that base URL.

Why:

- the gateway already exposes mailbox listing through `POST /v1/mail/check`
- listing unread mail is mailbox work that belongs to the agent’s workflow, not to notifier prompt assembly
- removing prompt-level mail summaries reduces prompt size and removes duplicated state narration

Alternative considered:

- keep summaries in the prompt and let the agent optionally re-check
  Rejected because it preserves duplicated mailbox-state presentation and keeps the notifier prompt more stateful than necessary.

### 2. Treat `houmao-process-emails-via-gateway` as a strict notifier-round workflow

The round-oriented workflow skill will assume the current round already provides the gateway base URL. It will instruct the agent to list unread mail itself with the gateway API, choose relevant mail for the round, complete the work, mark only successful mail read, and stop.

Why:

- notifier-driven rounds already have a live gateway base URL at wake-up time
- keeping the workflow skill strict prevents it from drifting into an ad hoc discovery tool
- this enforces a clean contract between gateway wake-up and agent action-taking

Alternative considered:

- let the workflow skill rediscover the gateway base URL when it is missing
  Rejected because that hides notifier contract failures and weakens the boundary between the wake-up path and generic mailbox operations.

### 3. Keep `houmao-email-via-agent-gateway` generic and context-first

The lower-level gateway skill will no longer assume it was triggered by a notifier. It will tell the agent to use a gateway base URL already present in prompt/context when available, and to fall back to `houmao-mgr agents mail resolve-live` only when the URL cannot be determined from current context.

Why:

- this skill is useful outside notifier rounds
- prompt/history often already contain the exact base URL, so repeating discovery is unnecessary
- retaining a manager fallback keeps the skill operational in generic shared-mailbox sessions without forcing prompt-specific assumptions

Alternative considered:

- require all gateway skill uses to go through notifier-provided URLs
  Rejected because it would make the generic gateway skill unusable for operator-driven mailbox work.

### 4. Remove `pixi` from all agent-visible gateway mailbox contracts

Agent-visible prompts and projected mailbox skills will stop mentioning `pixi`. When manager-based discovery is still needed, the contract will reference `houmao-mgr agents mail resolve-live` directly.

Why:

- `pixi` is a development packaging concern, not part of the mailbox contract
- deployed installations are expected to expose Houmao commands directly
- agent guidance should depend on stable product surfaces, not repo-local bootstrap commands

Alternative considered:

- keep `pixi` in skill docs as one documented invocation option
  Rejected because it keeps development-only packaging details inside the runtime-owned agent contract.

### 5. Keep the existing gateway mailbox route set for this change

This change does not add new mailbox routes. The notifier prompt and workflow will rely on the existing shared gateway surface:

- `GET /v1/mail/status`
- `POST /v1/mail/check`
- `POST /v1/mail/send`
- `POST /v1/mail/reply`
- `POST /v1/mail/state`

Why:

- the existing routes are already sufficient for agent-side unread listing and bounded-round processing
- this keeps the change focused on prompt and skill contracts instead of broadening scope into new mailbox API design

Alternative considered:

- add a dedicated `read` or bootstrap route in the same change
  Deferred because the current route set already supports the required workflow.

## Risks / Trade-offs

- [Prompt loses pre-rendered unread summaries] → The agent must always perform an explicit mailbox check at round start; this is acceptable because that is now the intended workflow.
- [Strict notifier workflow may fail harder when a wake-up prompt omits the base URL] → Treat that as a gateway prompt contract bug and cover it with notifier prompt tests.
- [Generic gateway skill still depends on manager fallback outside notifier rounds] → Keep that fallback explicit, context-first, and free of `pixi` so the boundary remains stable for deployed environments.
- [Transport-specific skills may drift if they duplicate old resolver wording] → Update transport-specific skills and associated tests in the same change.

## Migration Plan

1. Revise the packaged notifier prompt template and runtime renderer together.
2. Update projected gateway and processing mailbox skills to the new bootstrap contract.
3. Update transport-specific mailbox skills so they reference the new gateway/bootstrap guidance.
4. Update notifier prompt and mailbox skill tests to assert the new prompt content and discovery rules.
5. Roll forward without a compatibility shim; old prompts and skill wording are runtime-owned assets and may change in place.

## Open Questions

- None for proposal scope. The existing shared mailbox route set is sufficient for this change; dedicated read/bootstrap route refinements can be considered later if workflow ergonomics still need improvement.
