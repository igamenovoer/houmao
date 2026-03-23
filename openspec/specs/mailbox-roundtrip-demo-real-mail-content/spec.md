# mailbox-roundtrip-demo-real-mail-content Specification

## Purpose
TBD - created by archiving change add-mailbox-roundtrip-real-mail-content-verification. Update Purpose after archive.

## Requirements

### Requirement: Successful mailbox roundtrip automation SHALL persist inspectable canonical mailbox content
The mailbox roundtrip tutorial-pack automation SHALL leave real filesystem-mailbox message artifacts under the selected demo output directory after a successful roundtrip.

A successful run SHALL produce canonical Markdown message documents for the initial send and the reply under `<demo-output-dir>/shared-mailbox/messages/<YYYY-MM-DD>/`, along with the corresponding projection and SQLite state needed to inspect the thread from the demo mailbox root.

#### Scenario: Auto run leaves canonical send and reply content on disk
- **WHEN** a maintainer runs `run_demo.sh auto --demo-output-dir <path>` successfully
- **THEN** `<path>/shared-mailbox/messages/` contains canonical message documents for the initial message and the reply
- **AND THEN** the initial message body matches the tracked demo initial-message Markdown input and the reply body matches the tracked reply-message Markdown input
- **AND THEN** the reply document threads back to the initial message through its canonical mailbox metadata

#### Scenario: Stepwise run keeps canonical mailbox content inspectable after stop
- **WHEN** a maintainer runs `run_demo.sh start`, `run_demo.sh roundtrip`, `run_demo.sh verify`, and `run_demo.sh stop` against one selected demo output directory
- **THEN** the canonical mailbox message documents and mailbox projections remain inspectable under that same `<demo-output-dir>/shared-mailbox/` after `stop`
- **AND THEN** the completed demo root can be examined without re-running the roundtrip

### Requirement: Mailbox roundtrip regression automation SHALL verify real message content instead of synthetic step results alone
The pack-local mailbox roundtrip regression automation SHALL validate real canonical mailbox artifacts created by a successful scenario run.

Automated success cases SHALL fail if the demo reports a successful roundtrip but no canonical send and reply message documents were actually written into the mailbox root.

#### Scenario: Scenario automation checks canonical mailbox bodies against tracked demo inputs
- **WHEN** the pack-local scenario runner executes a successful mailbox roundtrip scenario
- **THEN** automated verification compares the parsed canonical send and reply message bodies against the tracked tutorial input Markdown files
- **AND THEN** a canned message ID, unread count, or other synthetic JSON step result is not sufficient on its own to satisfy the scenario

#### Scenario: Scenario evidence identifies where maintainers can inspect canonical messages
- **WHEN** a successful roundtrip scenario finishes
- **THEN** the machine-readable scenario evidence identifies stable canonical mailbox paths, message IDs, or equivalent inspection pointers for the send and reply messages
- **AND THEN** a maintainer can locate the persisted mailbox content under the scenario's demo output directory

### Requirement: Sanitized demo verification SHALL remain separate from raw mailbox content
The mailbox roundtrip demo SHALL preserve its sanitized verification contract even when automation now leaves real canonical mailbox content on disk.

Tracked verification snapshots SHALL continue to avoid embedding raw mailbox message bodies or other unstable canonical-content payloads.

#### Scenario: Snapshot verification stays sanitized while canonical messages remain available
- **WHEN** a maintainer runs `run_demo.sh verify` or `run_demo.sh verify --snapshot-report` after a successful roundtrip
- **THEN** the tracked verification output remains sanitized and excludes raw canonical message body content
- **AND THEN** the actual canonical send and reply Markdown documents remain available under `<demo-output-dir>/shared-mailbox/` for manual inspection
