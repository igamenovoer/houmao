## 1. Shared Mailbox Lifecycle Model

- [ ] 1.1 Update shared mailbox message/state models to expose `read`, `answered`, `archived`, and box membership without treating read state as completion.
- [ ] 1.2 Replace read-only state mutation request handling with list, peek, read, mark, move, and archive operation models while preserving opaque `message_ref` targeting.
- [ ] 1.3 Ensure successful reply operations automatically mark the replied message `answered=true` and `read=true` without archiving it.

## 2. Filesystem Transport

- [ ] 2.1 Update filesystem mailbox-local schema/state handling to persist answered state and active box membership alongside read and archived state.
- [ ] 2.2 Implement filesystem list, peek, read, mark, move, and archive operations with existing mailbox lock discipline and immutable canonical Markdown content.
- [ ] 2.3 Make `archive/` an active per-account mailbox box and update projection handling so archived mail leaves open inbox work.
- [ ] 2.4 Update filesystem reindex, repair, export, and clear-message paths so they preserve or rebuild the new lifecycle state consistently.

## 3. Stalwart Transport

- [ ] 3.1 Extend the Stalwart JMAP client and adapter to list supported boxes, peek/read messages, set seen/read state, and report answered/archive state.
- [ ] 3.2 Implement JMAP-backed mark, move, and archive behavior using server mailbox membership and answered/seen keywords or equivalent durable metadata.
- [ ] 3.3 Update Stalwart reply handling so successful replies mark the parent message answered and read through the same shared lifecycle contract.

## 4. Gateway API

- [ ] 4.1 Replace gateway mail check/state request and response models with status, list, peek, read, send, post, reply, mark, move, and archive models in `gateway_models.py`.
- [ ] 4.2 Extend `GatewayMailboxAdapter` and filesystem/Stalwart gateway adapters with lifecycle methods for list, peek, read, mark, move, archive, and reply-state updates.
- [ ] 4.3 Update `gateway_service.py` routes to expose `/v1/mail/list`, `/v1/mail/peek`, `/v1/mail/read`, `/v1/mail/mark`, `/v1/mail/move`, and `/v1/mail/archive`, and remove unused `/v1/mail/check` and `/v1/mail/state` handlers.
- [ ] 4.4 Keep `POST /v1/mail/archive` as a shortcut that delegates to the same adapter path as a move to the archive box and returns verified lifecycle state.
- [ ] 4.5 Update gateway route validation, loopback-only policy, status payloads, and error behavior for unsupported boxes or transport capabilities.

## 5. CLI and Fallback Mail Prompts

- [ ] 5.1 Update `houmao-mgr agents mail` commands to expose `list`, `peek`, `read`, `mark`, `move`, and `archive`, while retiring `check` and `mark-read` from the current lifecycle workflow.
- [ ] 5.2 Update managed-agent fallback mail prompt generation and result parsing so fallback operations understand the revised lifecycle action names and output payloads.
- [ ] 5.3 Preserve existing authority-aware result semantics for verified gateway/manager execution versus non-authoritative TUI fallback submission.

## 6. Mail Notifier

- [ ] 6.1 Change notifier polling to list open inbox work rather than unread-only mail, including read or answered messages that remain unarchived.
- [ ] 6.2 Update notifier digest, audit records, logs, and status summaries from unread-set terminology to open-work terminology where behavior changes.
- [ ] 6.3 Update notifier prompt rendering and endpoint URL blocks to direct agents to list, peek, read, reply, mark, move, and archive operations, with archive as completion.
- [ ] 6.4 Keep existing prompt-readiness and gateway queue-admission gates unchanged while changing only the mailbox eligibility input.

## 7. Skills and Documentation

- [ ] 7.1 Update `houmao-process-emails-via-gateway` to use open inbox work, list/peek/read triage, reply/ack answered semantics, and archive-after-processing.
- [ ] 7.2 Update `houmao-agent-email-comms` action pages and references to cover status, list, peek, read, send, post, reply, mark, move, archive, and resolve-live.
- [ ] 7.3 Update gateway, mailbox-manager, touring, and other affected Houmao system-skill references that still mention `check`, `/v1/mail/state`, or `mark-read` as current ordinary mailbox workflow.
- [ ] 7.4 Update CLI, mailbox, gateway notifier, and mailbox skill reference docs to match the revised lifecycle and endpoint contract.

## 8. Tests

- [ ] 8.1 Add unit coverage for filesystem lifecycle state transitions, active archive projections, and peek-versus-read behavior.
- [ ] 8.2 Add unit coverage for Stalwart JMAP lifecycle mapping, including read, answered, move, and archive behavior.
- [ ] 8.3 Add gateway API tests for list, peek, read, mark, move, archive, and automatic answered state after reply.
- [ ] 8.4 Add CLI tests for new `agents mail` commands and removal of the old current workflow commands.
- [ ] 8.5 Add notifier tests proving read-but-unarchived and answered-but-unarchived inbox messages still trigger reminders, while archived messages do not.
- [ ] 8.6 Run `pixi run lint`, `pixi run typecheck`, and targeted mailbox/gateway test suites before marking the change complete.
