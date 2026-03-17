## ADDED Requirements

### Requirement: Repository SHALL provide an opt-in real-agent mailbox smoke entrypoint
The repository SHALL provide an opt-in smoke entrypoint for `scripts/demo/mailbox-roundtrip-tutorial-pack` that uses the operator's actual local Claude/Codex CLIs and credentials through the normal `start-session` and runtime `mail` control path.

That smoke entrypoint SHALL NOT run as part of the default fast test suite. It SHALL require explicit maintainer opt-in through a manual script, an env-gated test target, or an equivalent clearly non-default invocation.

The real-agent smoke entrypoint SHALL use the mailbox tutorial pack with the dedicated dummy-project workdir fixture and the lightweight mailbox-demo blueprints rather than the main-repo worktree plus heavyweight engineering roles.

#### Scenario: Explicitly invoked smoke entrypoint starts actual local tool sessions
- **WHEN** a maintainer explicitly invokes the real-agent smoke entrypoint with the required local Claude/Codex prerequisites available
- **THEN** the run starts the tutorial-pack sender and receiver through the normal `start-session` flow using the actual local CLI tools
- **AND THEN** the started sessions use the dummy-project/lightweight-role fixture shape rather than the main-repo/heavyweight-role fixture shape

#### Scenario: Missing real-agent prerequisites fail clearly
- **WHEN** a maintainer invokes the real-agent smoke entrypoint without the required local CLI tools, auth, or other prerequisites
- **THEN** the smoke entrypoint fails explicitly with prerequisite guidance
- **AND THEN** it does not silently skip into a fake-harness success path

### Requirement: Real-agent smoke SHALL preserve strict direct-path mailbox validation
The real-agent smoke entrypoint SHALL exercise mailbox send, check, and reply through the runtime-owned direct mail path and SHALL preserve the sentinel-delimited mailbox result contract as the correctness boundary.

The smoke entrypoint SHALL NOT satisfy the roundtrip requirement through mailbox file injection, gateway transport commands, or synthetic mailbox-result fallbacks.

#### Scenario: Real-agent smoke fails on direct-path mailbox errors
- **WHEN** the real-agent smoke entrypoint encounters a missing sentinel block, malformed mailbox result payload, prompt execution failure, or other direct-path mailbox error
- **THEN** the smoke run fails explicitly on that direct-path error
- **AND THEN** it does not report a successful mailbox roundtrip by synthesizing the missing result

### Requirement: Real-agent smoke SHALL surface in-flight inspection pointers for slow sessions
The real-agent smoke entrypoint SHALL publish enough information for a maintainer to inspect sender and receiver sessions while the run is in flight.

At minimum, the smoke lane SHALL surface the selected demo output directory and the pack-local inspection command or equivalent persisted coordinates needed to resolve tmux attach commands, terminal log paths, and live tool state for each tutorial participant.

#### Scenario: Maintainer can inspect slow sessions during a smoke run
- **WHEN** a maintainer starts the real-agent smoke entrypoint and one of the live mailbox turns runs slowly
- **THEN** the smoke output identifies how to inspect the sender or receiver session for that run
- **AND THEN** the maintainer can recover tmux attach and terminal-log watch coordinates without manually reverse-engineering the demo state layout
