## Why

When Houmao agents send mail to each other, the receiver first encounters a generic "you have mail in inbox" gateway notifier prompt and only sees per-message content after explicitly reading the inbox. That notifier prompt is a strong instruction-following surface, but today there is no way for a sender to attach short, prompt-visible guidance ("re-run on official timing path", "continue current task") to a mail message. Issue #48 asks for a sender-marked block that future notifier rendering can surface prominently while leaving ordinary message bodies unchanged.

Adding sender-controlled text to the receiver's instruction-following surface is a real trust shift. Rather than block the feature on solving sender authentication first, this change lays the protocol slot now so a follow-on notifier change can render the block under a switchable trust posture without another envelope-level breaking change later.

## What Changes

- **BREAKING**: extend the canonical mailbox message envelope with two new typed optional fields: `notify_block: str | None` and `notify_auth: MailboxNotifyAuth | None`. Bump `MAILBOX_PROTOCOL_VERSION`.
- Define a new sealed `MailboxNotifyAuth` model carrying `scheme`, `token`, `iss`, `iat`, `exp`. The only `scheme` value shipped in this change is `none`; the enum is fixed at `"none" | "shared-token" | "hmac-sha256" | "jws"` so future verifier work does not require another envelope bump.
- Define the body marker syntax: a Markdown fenced code block with info-string `houmao-notify`. Senders SHALL author the block in `body_markdown`; canonical-message construction SHALL extract the first such block into `notify_block` and leave the body source unchanged.
- Define maximum extracted block length (default 512 characters) at canonical-message construction; extraction beyond the cap SHALL truncate and record truncation through the canonical envelope, not silently drop content.
- Operator-origin send composes canonical messages directly and SHALL accept `notify_block` and `notify_auth` through the same extraction-and-validation path as ordinary send.
- `houmao-mgr agents mail send` and `houmao-mgr agents mail post` gain `--notify-block <text>` to override or supply the field independently of the body fence; the body fence remains the default authoring path.
- Define delivery, peek, and read flows: the canonical envelope SHALL preserve `notify_block` and `notify_auth` immutably alongside `body_markdown`. Per-recipient mailbox state SHALL NOT extend to these fields.

This change does **not**:
- render `notify_block` anywhere — the gateway notifier template remains content-free in this change.
- ship any verifier — `scheme="none"` is the only accepted value; non-`none` schemes are rejected at validation in this change.
- introduce gateway notifier configuration knobs or audit fields for verification.

Those land in a follow-on change (`render-mailbox-notify-blocks-in-gateway-notifier` or similar) once this protocol slot is in place.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-mailbox-protocol`: add the canonical `notify_block` and `notify_auth` envelope fields, the `MailboxNotifyAuth` sub-model, body-fence syntax, the extraction rule with size cap, and the protocol version bump.
- `agent-mailbox-operator-origin-send`: accept `notify_block` and `notify_auth` on operator-origin canonical message composition with the same extraction-and-validation contract as ordinary send.
- `houmao-srv-ctrl-native-cli`: extend `houmao-mgr agents mail send` and `houmao-mgr agents mail post` with a `--notify-block` flag and auto-extract from the `houmao-notify` body fence.

## Impact

- **Code**: `src/houmao/mailbox/protocol.py` (new fields + sub-model + version bump + extractor), `src/houmao/mailbox/filesystem.py` and `src/houmao/mailbox/stalwart.py` (envelope persistence), `src/houmao/mailbox/managed.py` (operator-origin send), `src/houmao/srv_ctrl/cli.py` (`agents mail send|post` flags), and the gateway `/v1/mail/send` handler in `src/houmao/agents/realm_controller/gateway_service.py` (accept the new fields, no rendering).
- **Stored data**: existing canonical messages without these fields remain valid (optional fields default to `None`). Newly composed messages MUST validate to the bumped protocol version.
- **Tests**: `tests/unit/mailbox/` for protocol model, extractor edge cases, size-cap truncation, and operator-origin paths; `tests/unit/srv_ctrl/` for CLI flags; `tests/integration/` for end-to-end filesystem-transport round-trips.
- **Docs**: update `docs/reference/mailbox/` envelope reference and `houmao-mgr agents mail` CLI reference.
- **Deferred**: the gateway notifier template change, the verifier plug interface and built-in verifiers, the gateway notifier config (`notify_block_render`, `notify_block_auth_mode`, `notify_block_auth_verifier`), and the audit-record additions all belong to the follow-on rendering change. This change locks the envelope shape so that follow-on can ship as a notifier-only modification without re-touching the protocol.
