## ADDED Requirements

### Requirement: Gateway reference documents diagnostic logging
The agent gateway reference documentation SHALL explain the opt-in gateway diagnostic logging feature.

At minimum, the documentation SHALL cover:

- how diagnostic logging differs from the human-oriented `gateway.log`,
- where diagnostic log files live under the gateway-owned log directory,
- how rotation and backup retention bound disk usage,
- which gateway events are captured when diagnostic logging is enabled,
- the redaction boundary for message bodies, prompt text, attachments, and secrets,
- how consecutive warning and error deduplication is represented,
- how diagnostic logs relate to durable state artifacts such as `queue.sqlite`, `events.jsonl`, `state.json`, and manifests,
- how cleanup commands treat diagnostic log files.

#### Scenario: Operator can find and interpret diagnostic logs
- **WHEN** an operator opens the gateway reference after enabling gateway diagnostic logging
- **THEN** the documentation identifies the diagnostic log location and file rotation behavior
- **AND THEN** the documentation explains how to interpret request, validation, mailbox, and dedup summary entries at the level needed for postmortem debugging

#### Scenario: Documentation states the redaction boundary
- **WHEN** a maintainer reads the gateway diagnostic logging documentation
- **THEN** the documentation states that diagnostic logs do not include mailbox bodies, raw prompts, attachment contents, authorization headers, cookies, bearer tokens, credential material, or environment secrets by default
- **AND THEN** the documentation points readers to durable gateway artifacts when queue or notifier state, rather than diagnostic logs, is the authoritative source of truth
