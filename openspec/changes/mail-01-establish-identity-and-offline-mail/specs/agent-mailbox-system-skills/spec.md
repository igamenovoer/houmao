# Spec Delta

## MODIFIED Requirements

### Requirement: Mailbox system skills use a stable resolver contract for current mailbox discovery
Projected mailbox skills SHALL discover current mail state through the scoped `houmao-mgr agents self mail resolve-live` or explicitly targeted `agents single` equivalent. The result SHALL expose both optional bindings, owner/channel/binding scope, revisions, canonical mail identity, safe operational information, and the current validated gateway endpoint. It SHALL not depend on inherited mailbox environment snapshots or expose credential material.

#### Scenario: Filesystem mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** an agent resolves its configured offline mail
- **THEN** it receives the current offline binding and selected registry context
- **AND THEN** it can use the supported facade without scraping tmux environment or raw manifests

#### Scenario: Stalwart mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** an agent resolves its configured Stalwart online mail
- **THEN** it receives the online provider identity and current binding revision alongside any offline binding
- **AND THEN** ordinary mailbox work does not require receiving a password or credential-file path

## ADDED Requirements

### Requirement: Mailbox skill workflows select channels explicitly
Ordinary and notifier-driven routines SHALL retain the selected channel and expected binding ID through mailbox operations. Canonical online-first identity SHALL not act as transport selection. A notifier round SHALL use its supplied channel, binding ID, and exact gateway endpoint. Binding mismatch SHALL end that round explicitly rather than silently switching to a replacement mailbox.

#### Scenario: Dual-mail agent processes an offline reminder
- **WHEN** the public agent entrypoint routes an offline notification round to its protected mailbox routine
- **THEN** every operation for that round uses the offline channel
- **AND THEN** the online canonical identity does not redirect the round

#### Scenario: Round lacks channel context
- **WHEN** a notifier-driven round has a gateway URL but no selected channel
- **THEN** the routine reports a contract error rather than guessing from the canonical address

### Requirement: Mailbox skill installation is independent of late binding health
Supported runtime prompts SHALL continue using the public agent entrypoint only when its required static routing siblings are installed. Otherwise they SHALL provide maintained API guidance for the selected channel without requiring a body restart, copying skills into project content, or claiming that newly written skill files are already known to a running CLI.

#### Scenario: Already-running mailbox-disabled body gains offline mail
- **WHEN** late registration enables offline mail on a body without an available native mailbox skill route
- **THEN** the notifier supplies the selected channel and direct API workflow
- **AND THEN** it does not require native skill hot-reload to make attachment actionable
