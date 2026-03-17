## ADDED Requirements

### Requirement: Tutorial-pack runner SHALL manage loopback CAO lifecycle with aligned launcher state by default
When the mailbox roundtrip tutorial pack targets a supported loopback CAO base URL, the runner SHALL manage CAO lifecycle through a demo-local launcher config rather than assuming an ambient CAO server is already configured correctly.

That default loopback path SHALL:

- write a launcher config under the demo-owned output tree,
- start or reuse CAO through `houmao.cao.tools.cao_server_launcher`,
- validate launcher ownership when reuse occurs,
- align `--cao-profile-store` with the launcher-managed CAO home for the selected base URL, and
- stop launcher-managed CAO on cleanup when the current run started it.

#### Scenario: Default loopback run auto-manages CAO
- **WHEN** a developer runs `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh` against the default loopback CAO base URL
- **THEN** the runner creates or reuses a launcher-managed CAO server for that demo run
- **AND THEN** both `start-session` calls receive a `--cao-profile-store` aligned with that launcher-managed CAO context
- **AND THEN** the runner stops the launcher-managed CAO server on cleanup when this run started it

#### Scenario: Demo-local launcher context controls CAO profile-store alignment
- **WHEN** the tutorial runner starts or reuses loopback CAO through its demo-local launcher config
- **THEN** the resolved `--cao-profile-store` comes from that demo-local launcher context rather than from unrelated ambient or repo-wide launcher state
- **AND THEN** both tutorial `start-session` calls use that resolved store consistently

#### Scenario: Cleanup stops only runner-started loopback CAO after partial or interrupted runs
- **WHEN** the default loopback tutorial path has started launcher-managed CAO and the run exits early, is interrupted, or fails before both agent sessions come up
- **THEN** the runner cleanup still stops that launcher-managed CAO if and only if the current run started it
- **AND THEN** the runner does not stop an external or previously running CAO instance that this run did not start

#### Scenario: Reused untracked CAO ownership fails clearly
- **WHEN** the tutorial runner encounters a healthy CAO server at the selected loopback base URL whose ownership cannot be verified through the launcher-managed artifact context
- **THEN** the runner retries through the launcher stop/start recovery path or fails explicitly with ownership diagnostics
- **AND THEN** it does not silently continue against an unknown CAO ownership context

### Requirement: Tutorial-pack documentation and verification SHALL reflect mailbox-local state explicitly
The mailbox roundtrip tutorial pack SHALL teach and verify the current filesystem mailbox state split:

- shared-root `index.sqlite` is shared structural catalog state,
- each resolved mailbox directory owns `mailbox.sqlite` for mailbox-view state,
- gateway notifier remains optional and is not part of the tutorial's core success path.

The README, generated report, and sanitized expected-report contract SHALL surface that state model explicitly enough that a developer following the tutorial is not left with the stale impression that all mutable mailbox state still lives only in the shared root.

#### Scenario: Tutorial output verifies mailbox-local state artifacts
- **WHEN** the tutorial pack completes successfully
- **THEN** its verification flow confirms that the shared mailbox root contains the shared `index.sqlite`
- **AND THEN** it confirms that both tutorial mailbox directories contain mailbox-local `mailbox.sqlite` state
- **AND THEN** the sanitized report masks those concrete paths reproducibly

#### Scenario: Tutorial remains gateway-optional
- **WHEN** a developer follows the mailbox roundtrip tutorial exactly as documented
- **THEN** the tutorial succeeds through runtime `mail send`, `mail check`, `mail reply`, and `stop-session` commands without requiring gateway attach or mail-notifier enablement
- **AND THEN** any gateway notifier discussion is presented as optional follow-up context rather than as a hidden prerequisite
