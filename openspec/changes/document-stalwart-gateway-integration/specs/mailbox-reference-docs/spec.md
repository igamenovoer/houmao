## ADDED Requirements

### Requirement: Mailbox reference documentation provides a Stalwart-first-session reader path
The mailbox reference documentation SHALL provide a clear first-session reader path for Stalwart-backed mailbox use instead of requiring readers to infer that path from filesystem-first pages or low-level contract references.

At minimum, the mailbox reference SHALL:

- make the transport choice visible from the mailbox entry path or quickstart,
- provide a dedicated Stalwart-focused operations page under the mailbox subtree,
- explain the prerequisites and Houmao-side assumptions for a Stalwart-backed session,
- explain how to start a mailbox-enabled session with the `stalwart` transport,
- explain how to verify the first session with `mail check`, `mail send`, and `mail reply`,
- explain that a live gateway mailbox facade becomes the preferred shared path when it is attached.

The Stalwart-focused guidance SHALL include at least one transport-comparison artifact such as a table that helps new readers distinguish filesystem-backed and Stalwart-backed sessions before the docs dive into detailed contracts.

#### Scenario: Reader can choose the Stalwart path from mailbox quickstart
- **WHEN** a first-time reader opens the mailbox entry path to enable mailbox support
- **THEN** the mailbox docs make the transport choice visible near the start of that path
- **AND THEN** the Stalwart path links to a dedicated page that explains the first-session flow without requiring the reader to reconstruct it from low-level contract pages

#### Scenario: Operator can follow a Stalwart-backed first session safely
- **WHEN** an operator wants to start and verify a Stalwart-backed mailbox session
- **THEN** the mailbox operations docs explain the Houmao-side prerequisites, the `stalwart` session-start flow, and the first `mail check`, `mail send`, and `mail reply` steps
- **AND THEN** the same page explains when the operator should expect shared mailbox work to prefer a live gateway mailbox facade

### Requirement: Mailbox reference documentation explains shared mailbox boundaries across runtime, gateway, and transport
The mailbox reference documentation SHALL explain the shared mailbox abstraction boundaries now that filesystem-backed and Stalwart-backed transports both exist.

At minimum, the mailbox reference SHALL explain:

- the difference between direct transport-specific mailbox behavior and the shared gateway mailbox facade,
- that shared mailbox operations are transport-neutral even when implemented by transport-specific adapters underneath,
- that `message_ref` is an opaque shared reply target rather than a filesystem-only or Stalwart-only identifier contract,
- which exact payload and schema details remain centralized in the mailbox and gateway contract pages rather than being duplicated into narrative pages.

When this boundary explanation uses summaries or comparison tables, it SHALL preserve the current implemented v1 behavior rather than describing future transport abstractions as though they were already supported.

#### Scenario: Developer can see direct versus gateway mailbox paths clearly
- **WHEN** a developer opens the mailbox reference to understand how shared mailbox operations are performed
- **THEN** the mailbox docs explain the distinction between direct transport-specific behavior and the shared gateway mailbox facade
- **AND THEN** the reader can tell which path is preferred when a live gateway is attached

#### Scenario: Mailbox docs treat shared reply references as opaque
- **WHEN** a reader uses the mailbox reference to understand reply behavior across transports
- **THEN** the docs explain that `message_ref` is an opaque shared reply target
- **AND THEN** the docs do not present filesystem-specific identifiers or Stalwart-native identifiers as the universal mailbox reply contract
