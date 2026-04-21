## Why

Gateway mail-notifier now supports `pre_notification_context_action=compact`, but the current polling loop can re-run compaction for the same unchanged eligible inbox work on later cycles. That turns compaction from a one-time preparatory step into a noisy loop and can prevent the notifier from progressing cleanly to ordinary mailbox wake-up behavior.

## What Changes

- Change gateway mail-notifier behavior so pre-notification compaction runs at most once for a currently eligible mail item while that item remains eligible for the configured notifier mode.
- Preserve existing notifier wake-up semantics for unchanged eligible inbox work unless a separate product decision later changes prompt dedup behavior.
- Update notifier runtime bookkeeping so compaction history is tracked separately from notification timing or prompt-dedup state.
- Update gateway mail-notifier reference documentation to describe the new compaction-once behavior and remove wording that implies compaction runs before every repeated wake-up for unchanged mail.
- Add regression coverage for repeated polling with unchanged mail, plus mixed snapshots where new eligible mail appears while earlier eligible mail remains present.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway-mail-notifier`: change pre-notification compaction semantics so the same eligible mail does not trigger repeated compaction on later notifier cycles while it remains eligible.
- `docs-gateway-mail-notifier-reference`: update the gateway mail-notifier reference page so the documented polling cycle and repeat-notification notes match the new compaction-once behavior.

## Impact

- Affected code in `src/houmao/agents/realm_controller/gateway_service.py` and `src/houmao/agents/realm_controller/gateway_storage.py`.
- Affected tests under `tests/unit/agents/realm_controller/` and notifier integration coverage.
- Affected reference docs in `docs/reference/gateway/operations/mail-notifier.md`.
