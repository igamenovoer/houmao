## Context

The completed `mailbox-answered-archive-lifecycle` change separates message consumption from work completion: `read` means consumed, `answered` means replied or acknowledged, and `archive` closes inbox work. The gateway notifier already needs to wake on open inbox work by default so read-but-unarchived and answered-but-unarchived messages are not lost.

The remaining gap is configurability. Some operators still want a lower-noise notifier posture that behaves like the historical unread-only wake-up filter. That mode must be explicit because it can intentionally stop waking for read-but-unarchived work.

Current implementation context:

- Direct gateway notifier control uses `GET|PUT|DELETE /v1/mail-notifier`.
- Managed-agent pair and passive-server paths proxy the same gateway notifier models through `/houmao/agents/{agent_ref}/gateway/mail-notifier`.
- Native CLI control lives under `houmao-mgr agents gateway mail-notifier status|enable|disable`.
- Gateway notifier storage is a singleton durable row in the gateway queue database.
- The notifier prompt is rendered from `src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md`.

## Goals / Non-Goals

**Goals:**

- Add a durable notifier mode with values `any_inbox` and `unread_only`.
- Make `any_inbox` the default for omitted mode input.
- Use the mode only as the notifier eligibility filter.
- Preserve archive as the completion signal in both modes.
- Surface mode through direct gateway status, managed-agent proxy status, native CLI output, docs, and skill guidance.
- Make notifier prompt wording match the selected mode without reintroducing mark-read-as-completion.

**Non-Goals:**

- No per-sender, per-thread, subject, age, or custom predicate notifier filters.
- No digest-based deduplication change.
- No migration or compatibility shim for old gateway notifier SQLite rows beyond defaulting a missing stored mode to `any_inbox` when read.
- No change to the mailbox list/read/peek/reply/archive semantics themselves.
- No change to gateway request-admission, prompt-readiness, or busy-skip rules.

## Decisions

1. Model the mode as a small string enum.

   Use `any_inbox` and `unread_only` instead of a boolean such as `unread_only=true`. The enum keeps status payloads self-describing and leaves room for future modes without inverting boolean semantics later.

2. Store mode with notifier configuration and return it in status.

   The selected mode should survive gateway restart just like `enabled` and `interval_seconds`. `GatewayMailNotifierPutV1` should default omitted mode to `any_inbox`; `GatewayMailNotifierStatusV1` should always report the effective mode. When reading existing storage without a mode column or value, the effective mode should be `any_inbox`.

3. Apply mode only at the notifier poll boundary.

   The notifier should continue listing from `box="inbox"`, `answered_state="any"`, `archived=False`. The mode changes only `read_state`:

   - `any_inbox` -> `read_state="any"`
   - `unread_only` -> `read_state="unread"`

   This keeps the mailbox adapter contract small and avoids adding a second mailbox query surface just for notifier behavior.

4. Make prompt wording mode-aware but keep archive as completion.

   For `any_inbox`, the prompt should say open inbox mail exists and should direct the agent to list open inbox mail for the round. For `unread_only`, the prompt should say unread inbox mail triggered the notification and may direct the agent to start from unread inbox mail. In both cases the prompt must tell the agent to archive successfully processed mail and must not present `read` or `mark-read` as completion.

5. Treat `unread_only` as an explicit lower-noise trade-off.

   In `unread_only` mode, a message that has already been read or answered but remains unarchived will not by itself trigger future notifier prompts. This is acceptable because the operator explicitly chose the unread-only filter. Docs and skill guidance should name this trade-off directly.

6. Preserve proxy semantics through shared models.

   Direct gateway clients, server clients, passive-server clients, and native CLI commands should reuse the same notifier request/status models. The proxy layers should not reinterpret mode; they should validate and forward it exactly as part of the notifier payload.

## Risks / Trade-offs

- `unread_only` can hide read-but-unarchived work from future notifier prompts -> document it as an explicit lower-noise mode and keep `any_inbox` as the default.
- Existing notifier audit field names still use `unread_count` and `unread_digest` in some storage/model paths -> allow implementation to preserve storage names internally while user-facing docs, logs, and prompt text speak in mode-aware open-work terms.
- Mode-aware prompt text can drift from the installed processing skill -> update `houmao-process-emails-via-gateway` guidance to honor a prompt-provided mode while preserving the archive-after-processing rule.
- Existing gateway notifier rows will not have a mode value -> read missing mode as `any_inbox` and write it on the next notifier update; no broader migration is needed.
