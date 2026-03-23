# mailbox-roundtrip-direct-live-automation-test Specification

## Purpose
TBD - created by archiving change add-mailbox-roundtrip-direct-live-automation-test. Update Purpose after archive.

## Requirements

### Requirement: Automatic mailbox roundtrip testing SHALL leave two inspectable agent mailbox views with readable mail
Automatic testing for `scripts/demo/mailbox-roundtrip-tutorial-pack` SHALL, after a successful run, leave two inspectable per-agent mailbox directories plus canonical readable message documents under the selected demo output directory.

The automatic test SHALL validate the resulting mailbox artifacts by opening and reading the canonical Markdown messages from disk, not by relying only on step-result JSON or index metadata.

#### Scenario: Successful automatic run leaves readable send and reply mail on disk
- **WHEN** automatic testing runs the mailbox roundtrip tutorial pack successfully against a fresh `<demo-output-dir>`
- **THEN** `<demo-output-dir>/shared-mailbox/mailboxes/<sender-address>/` exists for the sender agent
- **AND THEN** `<demo-output-dir>/shared-mailbox/mailboxes/<receiver-address>/` exists for the receiver agent
- **AND THEN** canonical Markdown message documents for the initial send and reply exist under `<demo-output-dir>/shared-mailbox/messages/<YYYY-MM-DD>/`
- **AND THEN** the automatic test reads those canonical Markdown message documents from disk
- **AND THEN** the initial message body matches the tracked `inputs/initial_message.md` content and the reply body matches the tracked `inputs/reply_message.md` content

#### Scenario: Mail remains discoverable from both mailbox views after stop
- **WHEN** automatic testing completes a successful `start`, `roundtrip`, `verify`, and `stop` sequence for one fresh demo output directory
- **THEN** the sender mailbox view and receiver mailbox view remain inspectable under that same `<demo-output-dir>/shared-mailbox/mailboxes/`
- **AND THEN** inbox and sent projections for both agents resolve to the canonical send and reply message documents
- **AND THEN** a maintainer can locate and read the completed roundtrip mail without re-running the demo

### Requirement: Automatic mailbox roundtrip testing SHALL use the direct live-agent mail path
Automatic testing that claims to satisfy the direct live-agent mailbox contract SHALL start two actual local agents and perform mailbox send, check, and reply operations through the direct live-agent mail path, not through fake mailbox injection, not through gateway transport commands, and not through fake CLI stand-ins.

The qualifying automatic path SHALL resolve the actual local `claude` and `codex` executables together with real credential profiles selected by the tutorial-pack blueprints or explicit autotest-harness overrides.

Fake executables, deterministic stand-ins, or synthetic credential stores MAY remain useful for regression coverage, but they SHALL NOT satisfy this requirement even when they reuse the same underlying tutorial-pack flow.

#### Scenario: Real-agent harness uses actual local tools and credential profiles
- **WHEN** the tutorial pack executes its canonical `autotest/run_autotest.sh` case
- **THEN** it starts the sender and receiver through the normal `start-session` path using the actual local `claude` and `codex` tools
- **AND THEN** it resolves real credential material for both participants before the live roundtrip begins
- **AND THEN** it performs mailbox operations through the direct runtime mail path without gateway or fake-mail shortcuts

#### Scenario: Stand-in live coverage is not sufficient for the direct-live contract
- **WHEN** a deterministic harness reports a successful mailbox roundtrip while using fake `claude`, fake `codex`, fake credential material, or any other stand-in agent surface
- **THEN** that result does not satisfy the direct-live automation requirement
- **AND THEN** the real-agent harness requirement remains failing until the actual local tools produce the inspectable mailbox artifacts

### Requirement: Automatic mailbox roundtrip testing SHALL own isolated runtime state
Automatic testing SHALL use fresh and test-owned runtime state so that it can safely stop and restart its CAO server and avoid collisions with unrelated local agents.

#### Scenario: Automatic test uses fresh owned CAO and registry state
- **WHEN** the automatic test starts a mailbox roundtrip run
- **THEN** it selects a fresh `<demo-output-dir>`
- **AND THEN** it uses a test-owned loopback `CAO_BASE_URL` rather than assuming ambient ownership of `localhost:9889`
- **AND THEN** it uses an isolated `AGENTSYS_GLOBAL_REGISTRY_DIR` for the started agents
- **AND THEN** it may stop or restart that owned CAO instance as needed without relying on unrelated local state

#### Scenario: Ambient local state collisions fail the test instead of being hidden
- **WHEN** automatic testing encounters ambient CAO ownership conflicts, shared-registry conflicts, or other local-state contamination
- **THEN** the test SHALL surface that failure explicitly
- **AND THEN** the automatic workflow SHALL NOT silently fall back to synthetic mailbox success or a different non-owned state path

### Requirement: Sanitized verification SHALL remain separate from raw readable mail artifacts
The tutorial pack SHALL continue to keep sanitized verification artifacts separate from the raw mailbox messages that maintainers inspect on disk.

#### Scenario: Verification remains sanitized while readable mail stays on disk
- **WHEN** the automatic test runs `run_demo.sh verify` after a successful live roundtrip
- **THEN** the sanitized verification output excludes raw message body content
- **AND THEN** the readable canonical message Markdown files remain available under `<demo-output-dir>/shared-mailbox/` for inspection
