## Why

The previous change (`add-mailbox-notify-prompt-block`, eb828537) added the canonical `notify_block` envelope slot but left it invisible to the receiver agent. Until the gateway notifier renders the block, sender-marked guidance is stored in the canonical envelope and only surfaces if the receiver opens the message body. That gap blocks the original use case from issue #48 (short, prominent operator guidance reaching the receiver before they read mail) and leaves the trust knobs we shipped untested in flight.

The shipped slot also has an implementation gap that became visible during demo design: when a sender supplies `--notify-block "X"` directly without authoring a body fence, the canonical envelope ends up with `notify_block="X"` but `body_markdown` does not contain the same text. That makes `notify_block` a hidden channel — the receiver never sees the content if they only ever read mail. The intended invariant is that `notify_block` is a *priority surface*, not a *covert channel*: the same content always lives in `body_markdown` so a real-mail downstream (Stalwart, JMAP-projection, plain RFC 5322 readers) sees the wrapped content as ordinary fenced Markdown.

This change ships notifier rendering, the verifier interface, the gateway-side trust posture, the auto-mirror invariant that closes the hidden-channel gap, and a deliberately-injecting demo that makes the whole channel observable end-to-end.

## What Changes

- **BREAKING**: restructure `MailboxMessage.notify_block` from `str | None` to a typed sub-model `MailboxNotifyBlock | None` with fields `text: str` and `placement: Literal["append", "prepend"] = "append"`. Bump `MAILBOX_PROTOCOL_VERSION` to `3`. The previously shipped v2 envelope is unreleased; this change replaces it in place rather than carrying forward the bare-string form.
- **BREAKING**: enforce the **auto-mirror invariant** — when a sender supplies `notify_block` directly, canonical-message construction SHALL synthesize a ` ```houmao-notify ` fenced code block in `body_markdown` at the requested `placement` if and only if the body does not already contain a `houmao-notify` fence. Body content is otherwise left unchanged. This guarantees `notify_block.text` always appears verbatim somewhere in `body_markdown`.
- Add a new gateway notifier template slot `{{NOTIFY_BLOCKS_PREPEND}}` and `{{NOTIFY_BLOCKS_APPEND}}` so notify-block content can be rendered before or after the standard notifier prompt body, governed by the per-block `placement` metadata.
- Define a pluggable `NotifyAuthVerifier` interface and ship two built-in verifiers: `PermissiveVerifier` (always passes; v1 default) and `SharedTokenVerifier` (compares `notify_auth.token` against a configured allowlist). The protocol's reserved `hmac-sha256` and `jws` schemes remain reserved with no shipping verifier in this change.
- Add gateway notifier configuration knobs:
  - `notify_block_render: enabled | disabled` (default `enabled`)
  - `notify_block_auth_mode: permissive-log | required` (default `permissive-log`)
  - `notify_block_auth_verifier: none | shared-token` (default `none`)
  - `notify_block_per_message_chars: int` (default 512, identical to protocol cap)
  - `notify_block_total_chars: int` (default 2048; aggregate cap across all rendered blocks per notifier prompt)
- Extend the gateway notifier audit record with per-rendered-block entries: `message_ref`, `auth_scheme`, `auth_outcome` (`skipped` | `passed` | `failed`), `auth_detail`, `block_chars`, `block_truncated`.
- Extend `houmao-mgr agents mail send` and `houmao-mgr agents mail post` with `--notify-block-placement [append|prepend]` (default `append`) so the existing `--notify-block` flag can be paired with a placement choice.
- Add `single-agent-mail-prompt-injection/` runnable demo under `scripts/demo/` with two lanes (`claude`, `codex`) and two modes (`permissive-log` for the attack, `required` for the defense); demonstrates the notify-block channel reaching the receiver's wake-up prompt and the verifier mitigating that reach.

This change does **not**:
- ship a real verifier for `hmac-sha256` or `jws` schemes; those remain reserved-but-unsupported, rejected at validation as today.
- back-port any v2-shaped envelopes; v2 was unreleased so no in-the-wild data exists to migrate.
- introduce per-recipient state for notification blocks; the field stays part of the immutable canonical envelope.

## Capabilities

### New Capabilities

- `single-agent-mail-prompt-injection-demo`: runnable single-agent demo under `scripts/demo/` that drives operator-origin notify-block injection through the gateway notifier wake-up surface, with attack and defense lanes for matrix observation across supported tools.

### Modified Capabilities

- `agent-mailbox-protocol`: replace the `notify_block: str | None` field with the typed `MailboxNotifyBlock` sub-model carrying `text` and `placement`, define the auto-mirror invariant at composition, and bump `MAILBOX_PROTOCOL_VERSION` to `3`.
- `agent-gateway-mail-notifier`: render notify-block content into the wake-up prompt at the requested `placement`, run a pluggable verifier when one is configured, gate rendering on configurable trust posture (`permissive-log` default), enforce per-message and total size caps, and extend the audit record with per-block verification outcomes.
- `agent-mailbox-operator-origin-send`: accept the typed `MailboxNotifyBlock` shape, including placement-aware auto-mirroring into operator-origin canonical messages.
- `houmao-srv-ctrl-native-cli`: add `--notify-block-placement [append|prepend]` to `agents mail send` and `agents mail post`, default `append`; surface the canonical auto-mirror outcome and verifier-rejection paths through clean CLI errors.

## Impact

- **Code**: `src/houmao/mailbox/protocol.py` (typed sub-model, auto-mirror, version bump), `src/houmao/mailbox/managed.py` (operator-origin composition path), `src/houmao/agents/realm_controller/gateway_mailbox.py` (typed-shape pass-through), `src/houmao/agents/realm_controller/gateway_models.py` (request models accept typed shape), `src/houmao/agents/realm_controller/gateway_service.py` (notifier verifier wiring + config + audit), `src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md` (template slot additions), `src/houmao/agents/realm_controller/gateway_storage.py` (notifier record fields), `src/houmao/srv_ctrl/commands/agents/mail.py` and `src/houmao/srv_ctrl/commands/managed_agents.py` (placement flag plumbing), and a new `scripts/demo/single-agent-mail-prompt-injection/` tree.
- **Stored data**: the bumped protocol version means newly composed envelopes are `protocol_version=3`; v2 envelopes (unreleased) are no longer accepted. Filesystem mailbox stores written under prior demo runs should be reset per the demo harness's normal cleanup.
- **Tests**: extend protocol model tests for the typed sub-model, placement validation, and auto-mirror; add notifier renderer tests covering placement-aware rendering, multiple unread mails, size caps, verifier-skip, verifier-pass, verifier-fail; add CLI tests for the placement flag; add demo smoke tests reasonable to run in CI lanes that already cover demo packs.
- **Docs**: refresh `docs/reference/mailbox/contracts/canonical-model.md`, `docs/reference/cli/agents-mail.md`, `docs/reference/gateway/contracts/protocol-and-state.md`, and `docs/reference/managed_agent_api.md` for the typed shape, placement, auto-mirror, renderer, verifier, and demo.
- **Future-mail-system compatibility**: by treating the `houmao-notify` body fence as the source of truth and keeping `notify_block` as a parsed convenience surface, the design extends naturally to transports without a privileged control channel (Stalwart JMAP projection, future SMTP relays). Receivers that do not parse the fence simply see ordinary fenced Markdown in the body; Houmao-aware receivers extract and render. No covert metadata travels separately from the body.
