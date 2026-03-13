# Email Header Mapping

Use this reference when you need the exact mapping between the canonical mailbox protocol and a future true-email transport.

## Canonical to email header mapping

- `message_id` -> `Message-ID`
- `created_at_utc` -> `Date`
- sender -> `From`
- primary recipients -> `To`
- copied recipients -> `Cc`
- explicit reply target -> `Reply-To`
- `subject` -> `Subject`
- `in_reply_to` -> `In-Reply-To`
- `references` -> `References`
- `thread_id` -> `X-Agent-Thread-ID`
- extra protocol metadata -> `X-Agent-*`

## Rules

- Preserve `Message-ID`, `In-Reply-To`, and `References` as authoritative threading ancestry for the mail transport.
- Preserve `thread_id` through explicit protocol metadata rather than inferring thread identity from subject lines.
- Keep the body Markdown-compatible.
- Preserve attachment reference metadata so the canonical mailbox model can be reconstructed after normalization.
- This change defines the mapping only; it does not implement a working mail service.

## Guardrails

- Do not infer canonical thread identity from `Subject` alone.
- Do not discard `X-Agent-*` metadata needed to round-trip back into the canonical mailbox model.
- Do not assume internet mail behavior; this transport is localhost-scoped.
