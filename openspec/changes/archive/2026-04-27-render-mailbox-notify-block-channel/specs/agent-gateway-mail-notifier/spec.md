## ADDED Requirements

### Requirement: Gateway notifier renders sender-marked notification blocks at the requested placement
When the gateway notifier wakes a managed-agent target with one or more eligible unread mailbox messages whose canonical envelopes carry a non-null `notify_block`, the notifier prompt SHALL surface the `notify_block.text` of each rendered message at the position dictated by `notify_block.placement`.

The notifier prompt template SHALL expose two slots:

- `{{NOTIFY_BLOCKS_PREPEND}}` — rendered before the existing `"You have mail in inbox."` opener,
- `{{NOTIFY_BLOCKS_APPEND}}` — rendered after the existing mailbox API summary and notifier appendix block.

For each eligible unread message whose canonical envelope is rendered, the notifier SHALL emit one entry into the slot matching `notify_block.placement`. Entries SHALL be ordered oldest-first within each slot to match existing notifier nomination ordering.

Each rendered entry SHALL include a sender-attribution prefix that names the canonical sender principal address and the rendered `notify_block.text`. The prefix SHALL make it visually clear that the rendered text is sender-supplied content, not Houmao-owned notifier guidance.

When no eligible unread message carries a non-null `notify_block`, both slots SHALL render as empty content and SHALL NOT emit empty section headers.

The notifier SHALL apply two size caps when rendering:

- a per-message cap, defaulting to 512 characters and matching the canonical envelope's stored cap,
- a per-prompt aggregate cap across all rendered blocks, defaulting to 2048 characters.

When the aggregate cap is reached, additional eligible blocks SHALL be summarized as `"+ N more sender notice(s) — open inbox to read"` rather than truncated mid-content.

#### Scenario: Single unread mail with prepend placement renders before the inbox opener
- **WHEN** the gateway notifier wakes a managed-agent target with exactly one eligible unread mailbox message whose canonical envelope sets `notify_block.text="continue current task"` and `notify_block.placement="prepend"`
- **AND WHEN** the configured verifier is `none` and `notify_block_auth_mode` is `permissive-log`
- **THEN** the rendered notifier prompt contains the text `"continue current task"` before the line `"You have mail in inbox."`
- **AND THEN** the rendered prompt names the canonical sender principal address as the source of that notice

#### Scenario: Append placement renders after the mailbox API summary
- **WHEN** the gateway notifier wakes a managed-agent target with exactly one eligible unread mailbox message whose canonical envelope sets `notify_block.text="re-run on official path"` and `notify_block.placement="append"`
- **THEN** the rendered notifier prompt contains the text `"re-run on official path"` after the mailbox API summary
- **AND THEN** the rendered prompt names the canonical sender principal address as the source of that notice

#### Scenario: Multiple notify blocks cluster by placement and respect aggregate cap
- **WHEN** the gateway notifier wakes a managed-agent target with five eligible unread mailbox messages whose canonical envelopes each carry a non-null `notify_block` with mixed placement values, where the cumulative rendered text exceeds the aggregate cap
- **THEN** prepend-placement entries appear together before the inbox opener and append-placement entries appear together after the mailbox API summary
- **AND THEN** entries beyond the aggregate cap are summarized as a `"+ N more sender notice(s) — open inbox to read"` line
- **AND THEN** entries are ordered oldest-first within each placement cluster

#### Scenario: No eligible notify_block content yields no extra slot output
- **WHEN** the gateway notifier wakes a managed-agent target with eligible unread mailbox messages that all have `notify_block=None`
- **THEN** the rendered notifier prompt contains no extra prepend or append section headers
- **AND THEN** the prompt shape matches the prior content-free notifier baseline

### Requirement: Gateway notifier verifies notify_auth through a pluggable verifier interface
The gateway notifier SHALL run a configurable verifier against each eligible message's `notify_auth` value before rendering its `notify_block` content.

The verifier interface SHALL accept the canonical message and its `notify_auth` value (which MAY be `None`) and SHALL return a structured outcome with fields `passed: bool`, `detail: str | None`, and `scheme: str` so notifier audit can record both the configured scheme and the per-message verification result.

The system SHALL ship two built-in verifier implementations:

- `PermissiveVerifier` — always returns `passed=true`. This implementation is the default when `notify_block_auth_verifier=none` is configured. It records `scheme="none"` and a stable `detail` value indicating that no verification was performed.
- `SharedTokenVerifier` — compares `notify_auth.token` against a configured allowlist of shared-secret tokens. When the supplied token matches an allowlist entry, the verifier returns `passed=true` with `scheme="shared-token"`. When the token is missing, blank, or unrecognized, it returns `passed=false` with a `detail` value explaining the rejection without echoing the supplied token value.

Other reserved schemes (`hmac-sha256`, `jws`) SHALL remain rejected by the canonical envelope validator in this protocol version; no shipping verifier consumes them.

#### Scenario: PermissiveVerifier accepts every notify_block and reports skipped scheme
- **WHEN** the gateway notifier renders an eligible mailbox message with `notify_auth=None` and `notify_block_auth_verifier=none`
- **THEN** the verifier outcome records `passed=true`, `scheme="none"`, and a non-null `detail` value
- **AND THEN** the rendered notifier prompt includes the `notify_block.text`

#### Scenario: SharedTokenVerifier accepts an allowlisted token
- **WHEN** the gateway notifier renders an eligible mailbox message with `notify_auth.scheme="none"`, `notify_auth.token="bearer-xyz"`, and `notify_block_auth_verifier=shared-token` configured with `bearer-xyz` in the allowlist
- **THEN** the verifier outcome records `passed=true`, `scheme="shared-token"`, and a non-null `detail` value
- **AND THEN** the rendered notifier prompt includes the `notify_block.text`

#### Scenario: SharedTokenVerifier rejects an unrecognized token without echoing it
- **WHEN** the gateway notifier renders an eligible mailbox message with a `notify_auth.token` value not present in the allowlist and `notify_block_auth_verifier=shared-token` configured
- **THEN** the verifier outcome records `passed=false`, `scheme="shared-token"`, and a `detail` value that does not include the rejected token text

### Requirement: Gateway notifier trust posture is configurable through `notify_block_auth_mode`
The gateway notifier SHALL accept a `notify_block_auth_mode` configuration value with two supported settings:

- `permissive-log` — the verifier runs and the result is captured in audit, but rendering proceeds regardless of the verification outcome. This is the default mode shipped in this change.
- `required` — the verifier runs and rendering proceeds only when the verification outcome reports `passed=true`. When `passed=false`, the notify_block content SHALL be suppressed from the rendered prompt and the audit row SHALL record the suppression.

The notifier SHALL also accept a `notify_block_render` configuration value with two supported settings:

- `enabled` — notify_block rendering proceeds per the rules above. This is the default.
- `disabled` — notify_block rendering is fully suppressed and audit rows record `rendered=false` with detail `"render disabled"`. The verifier SHALL still run when configured so audit captures consistent data.

#### Scenario: Permissive-log renders notify_block even when verification fails
- **WHEN** the gateway notifier configuration sets `notify_block_auth_mode=permissive-log` and `notify_block_auth_verifier=shared-token` with an empty allowlist
- **AND WHEN** an eligible mailbox message arrives with a non-null `notify_auth` whose token is not allowlisted
- **THEN** the rendered notifier prompt includes the `notify_block.text`
- **AND THEN** the audit row records `auth_outcome="failed"` for that message

#### Scenario: Required mode suppresses notify_block content on verification failure
- **WHEN** the gateway notifier configuration sets `notify_block_auth_mode=required` and `notify_block_auth_verifier=shared-token` with an empty allowlist
- **AND WHEN** an eligible mailbox message arrives with a non-null `notify_auth` whose token is not allowlisted
- **THEN** the rendered notifier prompt does not include the `notify_block.text` for that message
- **AND THEN** the audit row records `auth_outcome="failed"` and `rendered=false` for that message

#### Scenario: Disabled rendering suppresses notify_block content unconditionally
- **WHEN** the gateway notifier configuration sets `notify_block_render=disabled`
- **AND WHEN** an eligible mailbox message arrives with a non-null `notify_block` and `notify_auth.scheme="none"`
- **THEN** the rendered notifier prompt does not include the `notify_block.text`
- **AND THEN** the audit row records `rendered=false` with `auth_detail="render disabled"`

### Requirement: Gateway notifier audit rows record per-rendered-block verification outcomes
The gateway notifier audit record SHALL grow per-rendered-block entries that capture the verification outcome and rendered-content metadata for every eligible mailbox message whose canonical envelope carried a non-null `notify_block`.

Each per-block audit entry SHALL include:

- `message_ref` — opaque message reference for the rendered message,
- `rendered: bool` — whether the rendered notifier prompt actually included this block's text,
- `auth_scheme: str` — verifier scheme name reported by the verifier outcome,
- `auth_outcome: "skipped" | "passed" | "failed"` — verification result, where `skipped` indicates the configured verifier was the permissive default and the message had no `notify_auth`,
- `auth_detail: str | None` — non-secret diagnostic for the verification outcome,
- `block_chars: int` — length of the rendered text in characters after truncation,
- `block_truncated: bool` — whether the per-message size cap truncated the rendered text.

Eligible messages whose canonical envelope had `notify_block=None` SHALL NOT generate per-block audit entries. The notifier SHALL continue to emit the existing per-poll audit summary for the entire wake-up cycle in addition to the new per-block entries.

#### Scenario: Audit rows record per-rendered-block verifier outcome
- **WHEN** the gateway notifier wakes a target with two eligible mailbox messages, one with `notify_block` populated and one without
- **AND WHEN** the configured verifier passes for the populated message
- **THEN** the per-poll audit row contains exactly one per-block entry for the populated message with `rendered=true`, `auth_outcome="skipped"` or `auth_outcome="passed"` depending on configured verifier, and the rendered `block_chars` value
- **AND THEN** the audit row does not contain a per-block entry for the message without `notify_block`
