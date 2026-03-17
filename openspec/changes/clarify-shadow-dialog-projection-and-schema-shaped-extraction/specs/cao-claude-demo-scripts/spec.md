## MODIFIED Requirements

### Requirement: `cao-claude-tmp-write` creates and verifies a runnable code file under `tmp/`
The `scripts/demo/cao-claude-tmp-write/run_demo.sh` demo SHALL remain valid under the default `shadow_only` CAO runtime posture for Claude.

Its success criteria SHALL be the verified file side effect plus successful session completion. The demo SHALL NOT require the final runtime `done.message` to contain the exact agent reply text, and any recorded response text from that run SHALL be treated as optional or best-effort rather than as the authoritative correctness boundary.

#### Scenario: Running tmp-write demo succeeds even when the shadow-mode done message is neutral
- **WHEN** a developer runs `scripts/demo/cao-claude-tmp-write/run_demo.sh` with valid local CAO + credentials under the default shadow-first runtime posture
- **THEN** the generated code file exists under `tmp/` and running it prints the expected sentinel output
- **AND THEN** the demo does not fail solely because the final runtime `done.message` is a neutral shadow-mode completion message

### Requirement: `cao-claude-esc-interrupt` demonstrates interrupt + recovery
The `scripts/demo/cao-claude-esc-interrupt/run_demo.sh` demo SHALL remain valid under the default `shadow_only` CAO runtime posture for Claude.

When the demo needs reply text from the second prompt after recovery, it SHALL recover that text through an explicit shadow-aware extraction path rather than assuming CAO-native reply text in the final runtime `done.message`.

#### Scenario: Interrupt demo recovers second-answer text through a shadow-aware path
- **WHEN** a developer runs `scripts/demo/cao-claude-esc-interrupt/run_demo.sh` with valid local CAO + credentials
- **THEN** the demo sends `Esc`, the terminal returns to idle, and a second prompt completes successfully
- **AND THEN** any verified second-answer text comes from an explicit shadow-aware extraction path instead of from the neutral shadow-mode `done.message`
