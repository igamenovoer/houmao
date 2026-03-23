## MODIFIED Requirements

### Requirement: Repo-owned CAO session demo response-extraction helpers do not treat `done.message` as authoritative reply text
The demo-owned `extract_response_text()` helpers in `scripts/demo/cao-claude-session/run_demo.sh`, `scripts/demo/cao-codex-session/run_demo.sh`, and `scripts/demo/cao-claude-tmp-write/run_demo.sh` SHALL NOT treat the final `done` event `message` as authoritative reply text for default shadow-mode runs.

When those demos record response text, that helper logic SHALL recover text through an explicit shadow-aware extraction path or SHALL surface the value as clearly labeled optional/best-effort text instead.

#### Scenario: Session demo helper no longer reads shadow-mode `done.message` as the answer
- **WHEN** a developer runs one of the repo-owned Claude or Codex CAO session demos under the default shadow-first posture
- **THEN** the demo's response-extraction helper does not treat the final runtime `done.message` as the authoritative reply text
- **AND THEN** any recorded response text comes from explicit shadow-aware extraction or is clearly labeled as optional/best-effort

### Requirement: `cao-claude-tmp-write` creates and verifies a runnable code file under `tmp/`
The `scripts/demo/cao-claude-tmp-write/run_demo.sh` demo SHALL remain valid under the default `shadow_only` CAO runtime posture for Claude.

Its success criteria SHALL be the verified file side effect plus successful session completion. The demo SHALL NOT require the final runtime `done.message` to contain the exact agent reply text, and any recorded response text from that run SHALL be treated as optional or best-effort rather than as the authoritative correctness boundary.

#### Scenario: Running tmp-write demo succeeds even when the shadow-mode done message is neutral
- **WHEN** a developer runs `scripts/demo/cao-claude-tmp-write/run_demo.sh` with valid local CAO + credentials under the default shadow-first runtime posture
- **THEN** the generated code file exists under `tmp/` and running it prints the expected sentinel output
- **AND THEN** the demo does not fail solely because the final runtime `done.message` is a neutral shadow-mode completion message

### Requirement: `cao-codex-session` remains valid under the default shadow-first runtime posture
The `scripts/demo/cao-codex-session/run_demo.sh` demo SHALL remain valid under the default `shadow_only` CAO runtime posture for Codex.

Its success criteria SHALL rely on successful session completion plus any explicitly documented shadow-aware or clearly labeled best-effort response extraction path, rather than on authoritative reply text from the final runtime `done.message`.

#### Scenario: Codex session demo succeeds without CAO-native reply text assumptions
- **WHEN** a developer runs `scripts/demo/cao-codex-session/run_demo.sh` with valid local CAO + credentials under the default shadow-first runtime posture
- **THEN** the session completes successfully without requiring authoritative reply text from the final runtime `done.message`
- **AND THEN** any recorded response text comes from the demo's explicit shadow-aware or clearly labeled best-effort extraction path

### Requirement: `cao-claude-esc-interrupt` demonstrates interrupt + recovery
The `scripts/demo/cao-claude-esc-interrupt/run_demo.sh` demo SHALL remain valid under the default `shadow_only` CAO runtime posture for Claude.

When the demo needs reply text from the second prompt after recovery, it SHALL recover that text through an explicit shadow-aware extraction path rather than assuming CAO-native reply text in the final runtime `done.message`.

#### Scenario: Interrupt demo recovers second-answer text through a shadow-aware path
- **WHEN** a developer runs `scripts/demo/cao-claude-esc-interrupt/run_demo.sh` with valid local CAO + credentials
- **THEN** the demo sends `Esc`, the terminal returns to idle, and a second prompt completes successfully
- **AND THEN** any verified second-answer text comes from an explicit shadow-aware extraction path instead of from the neutral shadow-mode `done.message`
