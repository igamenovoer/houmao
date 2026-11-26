# Design

## Context

The gateway already issues `msg_...` handles for incoming requests and attaches `event.handle` to successful send and reply results. Authorized history also issues current handles. Receipt lookup already uses a provider operation that checks visibility of the exact event using the bound Actor and Group before returning its retained attempts. The [proposal](proposal.md) describes the discovery problems this change addresses.

## Goals / Non-Goals

Give agents a short receipt target they already have. Make the correct CLI invocation discoverable before the agent needs to use it. Keep reads within the existing Actor binding and gateway permissions. The scope is receipt inspection, membership discovery, and CLI usage. CCCC remains the authority for stored events and delivery outcomes.

## Decisions

### Resolve Handles on the Existing Receipt Route

Extend `GET /v1/plugins/{instance}/chat/deliveries` with a `handle` query parameter. Accept exactly one `handle` or `event_ref` and validate cardinality and bounds before resolving it. Both selectors map to the same native event ID and call `chat.deliveries` with the requested `limit`. The route retains the `plugin.cccc.chat.deliveries.read` authorization action, the `1..100` limit with default `50`, and the current response and `has_more` semantics. The provider checks Actor visibility for either selector. Reusing the handle also gives the sender a short receipt target immediately after a successful send.

Use the same bounded handle store and scope checks as reply and details. The CLI takes the instance name from the handle when `--instance` is omitted and rejects an explicit mismatch. Gateway authorization still verifies the selected caller and endpoint. Expired, evicted, foreign, and retired handles get HTTP 409 `message_handle_stale`. Invalid scoped references keep HTTP 422 `reference_scope_error`. Both diagnostics direct the agent to select the exact event in authorized `chat history` and use its refreshed handle. A gateway connection change during a receipt request goes through the existing retired-connection check.

Gateway CLI accepts `--handle` and `--event-ref`. A raw `--event-id` in gateway mode returns `gateway_delivery_requires_event_ref_or_handle`; its guidance can point to `chat history --event-id EVENT_ID` for authorized lookup. Direct receipt inspection takes `--event-id` under the verified Actor profile and returns `direct_delivery_requires_event_id` for other target forms. Direct reply continues to use the Actor-scoped reference returned by direct pull, which help labels separately.

### Assert the Group in the Membership Request

When the CLI supplies `members --group`, map it to a single `expected_group_id` on the authorized gateway `GET /members` request. Check it against the selected instance's configured Group inside that route, before its existing provider call. This uses only `plugin.cccc.members.read` and keeps validation and membership tied to one binding. In direct mode, check the input against the Group in the verified Actor binding before issuing `members`. An omitted assertion skips the comparison. Both modes send the existing provider `members` request with its original argument shape.

A mismatch returns `group_conflict` with guidance to select the intended gateway URL and instance or direct profile. The gateway uses HTTP 409. Reject repeated, blank, overlong, and malformed assertions with a typed input error before membership projection. The actual selection always comes from the authenticated gateway binding or explicit profile. The assertion never appears in the returned member or error data.

### Put Exact Usage in the Installed CLI

Read `--version` from installed `houmao-cccc` distribution metadata when version is requested. Print `houmao-cccc VERSION` and exit zero before connection selection. Format top-level help with a gateway block, followed by a direct-profile block. The gateway block can use verified managed self, with a note about placing `--gateway-url`, `--instance`, and the signer binding when required before the command. Include examples with actual flags and explain where their inputs come from.

```bash
houmao-cccc binding
houmao-cccc members --group "$GROUP_ID"
houmao-cccc chat send --connection-token "$CONNECTION_TOKEN" --to "$ACTOR_ID" --operation-id "$SEND_ID" --mode request_reply --text 'Can you review this?'
houmao-cccc chat reply --handle "$HANDLE" --operation-id "$REPLY_ID" --text 'Reviewed.'
houmao-cccc chat history --limit 20
houmao-cccc chat deliveries --handle "$HANDLE"
```

Explain that `CONNECTION_TOKEN` comes from `members`, that a send returns `event.handle`, and that an incoming request supplies its own handle. Direct examples explicitly select `--direct-profile` and distinguish direct reply `--event-ref` from receipt `--event-id`. Put the target rules in `chat deliveries --help` and the assertion semantics in `members --help`. The existing compact fence already carries the required handle.

### Keep Diagnostics Safe Before Transport

Validate mode-specific delivery targets before profile lookup, request signing, or network access. Use fixed diagnostic codes and templates for usage mismatches and for the recognized remote scope or Group errors. On parser failures, use safe option identifiers and help pointers. Omit attached or following values and avoid raw parser or provider exception text. Preserve the gateway authorization and uncertain-mutation contracts for requests that reach transport.

## Risks / Trade-offs

- A short handle can expire or be evicted during a long task. Exact authorized history gives the caller a fresh handle. Existing scoped references remain valid where their existing scope permits them.
- A Group assertion could appear to grant authority to switch Groups. The checks only compare the expected value with the already selected binding and reuse its existing membership call.
- A help example can drift from parsing rules. Exercise the displayed commands in CLI tests and repeat the sender and recipient workflow against the installed package.

## Migration Plan

Deploy the updated wheel to the CLI and gateway environments together so the new options reach compatible routes. The CLI's version describes its own installed wheel. Existing callers using gateway `--event-ref`, direct `--event-id`, or `members` without an assertion can keep those invocations. The change uses the existing receiver-v2 service contract and stores no new persistent data. Rolling back the wheel restores the previous CLI and route behavior.
