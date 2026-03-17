## MODIFIED Requirements

### Requirement: Automatic mailbox roundtrip testing SHALL use the direct live-agent mail path
Automatic testing SHALL validate the mailbox tutorial pack through the direct runtime-owned `start-session` and `mail` control path rather than through mailbox file injection or gateway transport commands.

The automatic lane MAY replace external `claude`, `codex`, or `cao-server` executables with test-owned deterministic stand-ins, but it SHALL still drive the tutorial pack through the supported runtime/session surfaces and SHALL still require the direct mailbox result contract to succeed.

The automatic lane SHALL NOT use `attach-gateway`, `gateway-send-prompt`, or fake mailbox delivery helpers to satisfy the mailbox roundtrip requirement.

The automatic lane SHALL fail if the direct mail path returns a sentinel parse error, prompt execution failure, or any other direct-path mailbox failure.

Success of this deterministic automatic lane SHALL NOT be presented as proof that actual local Claude/Codex CLIs were exercised; that external-agent validation belongs to the separate opt-in real-agent smoke capability.

#### Scenario: Deterministic direct-path harness is required for a passing automatic test
- **WHEN** the automatic test executes the tutorial pack roundtrip
- **THEN** it starts two sessions through the supported `start-session` path
- **AND THEN** it performs mailbox operations through `run_demo.sh roundtrip`, `realm_controller mail ...`, or an equivalent direct runtime mail path
- **AND THEN** it MAY use test-owned fake CLI or CAO stand-ins to keep the run deterministic
- **AND THEN** it SHALL NOT use `attach-gateway`, `gateway-send-prompt`, or fake mailbox delivery helpers to satisfy the mailbox roundtrip requirement

#### Scenario: Deterministic harness fails on direct-path mailbox errors
- **WHEN** the deterministic automatic lane encounters a missing sentinel block, malformed mailbox result payload, prompt execution failure, or other direct-path mailbox failure
- **THEN** the automatic test fails on that direct-path error
- **AND THEN** it does not synthesize a successful mailbox roundtrip from mailbox-side effects alone

#### Scenario: Automatic direct-path success is not the same as actual local CLI coverage
- **WHEN** the deterministic automatic lane passes by using test-owned stand-ins for `claude`, `codex`, or `cao-server`
- **THEN** that result satisfies the automatic direct-path regression requirement
- **AND THEN** the repository still relies on the separate opt-in real-agent smoke lane for actual local Claude/Codex CLI validation
