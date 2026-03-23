# skill-invocation-demo-pack Specification

## Purpose
Define the tracked skill-invocation demo pack used for live installed-skill verification across Claude and Codex lanes.

## Requirements

### Requirement: Repository SHALL provide a skill-invocation demo pack under `scripts/demo/`
The repository SHALL include a self-contained demo pack under `scripts/demo/skill-invocation-demo-pack/` for live skill-invocation verification.

At minimum, that pack SHALL include:

- `README.md`
- `run_demo.sh`
- `inputs/`
- `scripts/verify_report.py`
- `expected_report/report.json`

The pack MAY include additional helper scripts, inspect helpers, or sanitized-report helpers when needed by the implementation, but the pack SHALL remain runnable from the repository checkout without hidden generated source files.

#### Scenario: Demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/skill-invocation-demo-pack/`
- **THEN** the required runner, inputs, verification helper, and expected-report files are present

### Requirement: Demo-pack runner SHALL support stepwise interactive skill-invocation checks for both Claude and Codex
The demo-pack runner SHALL support an operator workflow that can start a live session for a selected tool, inspect that running session, send the probe prompt, verify the skill side effect, and stop the session.

The pack SHALL support both `claude` and `codex` as selectable tool lanes rather than hard-coding one tool only.

The operator workflow SHALL remain stepwise and inspectable, not only one-shot automation.

The pack-local `run_demo.sh` surface SHALL support at minimum:

- `auto`
- `start`
- `inspect`
- `prompt`
- `verify`
- `stop`

The first version MAY add a separate real-agent `autotest/` harness later, but the supported live path for this change SHALL remain discoverable through `run_demo.sh`.

#### Scenario: Operator can run the demo stepwise for Claude
- **WHEN** a maintainer runs the skill-invocation demo for tool `claude`
- **THEN** the pack provides a stepwise path to start the session, inspect it, send the trigger prompt, verify the result, and stop the session

#### Scenario: Operator can run the demo stepwise for Codex
- **WHEN** a maintainer runs the skill-invocation demo for tool `codex`
- **THEN** the same pack supports the corresponding start, inspect, prompt, verify, and stop flow for the Codex session

#### Scenario: Operator can run the demo as one live `auto` flow
- **WHEN** a maintainer runs the skill-invocation demo pack without breaking the workflow into separate commands
- **THEN** the pack provides one `auto` path that performs the live start, prompt, verify, and stop sequence for the selected tool lane

### Requirement: Demo-pack stepwise commands SHALL reuse one selected demo output directory
The demo-pack runner SHALL preserve demo-owned state under one selected demo output directory so `start`, `inspect`, `prompt`, `verify`, and `stop` all act on the same copied dummy-project workdir and the same live session metadata for that run.

At minimum, the persisted demo-owned state SHALL be sufficient to recover:

- the copied project workdir,
- the runtime root or manifest coordinates,
- the selected tool lane,
- the expected probe output location, and
- the live-session identifiers needed for later inspect, verify, and stop commands.

#### Scenario: Stepwise commands reuse one selected demo root
- **WHEN** a maintainer runs `run_demo.sh start --demo-output-dir <path>`, later `run_demo.sh inspect --demo-output-dir <path>`, and then `run_demo.sh prompt --demo-output-dir <path>`
- **THEN** those commands operate on the same demo-owned copied project and persisted live-session state under `<path>`
- **AND THEN** the later commands do not need to reprovision a second unrelated demo workspace

### Requirement: Demo-pack runner SHALL provision a copied dummy-project workdir and a skill-enabled demo definition
The demo-pack runner SHALL provision a copied tracked dummy project into the demo-owned output root and initialize that copied tree as a standalone git-backed workdir for the run.

The runner SHALL start the selected live session from that copied dummy-project workdir rather than from the repository worktree.

The runner SHALL use tracked lightweight demo definitions that include the reusable dummy probe skill for the selected tool.

The selected live session SHALL use the current CAO `shadow_only` posture for that tool lane. Demo correctness SHALL continue to rely on the probe side effect rather than on authoritative reply text from the final runtime `done.message`.

#### Scenario: Demo run starts from a copied dummy-project workdir
- **WHEN** a maintainer starts the skill-invocation demo
- **THEN** the run provisions a copied tracked dummy project under the demo-owned output root
- **AND THEN** the launched agent session uses that copied tree as its workdir
- **AND THEN** the run does not depend on the main repository checkout as the launched workdir

#### Scenario: Selected tool session includes the tracked probe skill
- **WHEN** a maintainer starts the skill-invocation demo for one supported tool lane
- **THEN** the selected tracked demo definition includes the reusable probe skill fixture for that session
- **AND THEN** the live session starts with that probe skill available through the normal runtime skill-projection path

### Requirement: Demo-pack prompt contract SHALL test trigger-based skill invocation without install-path leakage
The demo-pack prompt used to trigger the probe skill SHALL NOT mention the skill install path and SHALL NOT require the operator-facing prompt to name the skill explicitly.

Instead, the prompt SHALL use trigger wording defined by the tracked probe-skill contract.

The success boundary for the demo SHALL be the observed probe side effect rather than a best-effort assistant reply alone.

The pack SHALL NOT require exact transcript recovery or authoritative final-answer text from the shadow-mode runtime result in order to treat a successful probe side effect as success.

#### Scenario: Probe prompt does not leak the skill install path
- **WHEN** the demo sends the trigger prompt to the selected live session
- **THEN** that prompt does not mention the internal skill install path
- **AND THEN** it does not require the operator-facing prompt to include the explicit skill package path

#### Scenario: Demo success is based on the probe side effect
- **WHEN** the selected live session handles the demo trigger successfully
- **THEN** the demo verifies success by observing the expected probe marker side effect in the demo-owned workdir
- **AND THEN** the demo does not rely only on freeform assistant prose as the correctness boundary

### Requirement: Demo-pack verification SHALL record and sanitize probe evidence
The demo pack SHALL generate a structured report that records the selected tool lane, trigger-prompt metadata, expected probe output location, observed probe evidence, and verification outcome.

Before comparing or refreshing `expected_report/report.json`, the demo tooling SHALL sanitize nondeterministic values such as timestamps, session identifiers, and absolute paths.

#### Scenario: Verification report captures probe evidence
- **WHEN** the skill-invocation demo reaches verification
- **THEN** the generated report includes the expected probe marker location and the observed probe evidence
- **AND THEN** the report states whether verification passed or failed for that run

#### Scenario: Snapshot refresh uses sanitized content only
- **WHEN** a maintainer refreshes the skill-invocation demo snapshot
- **THEN** `expected_report/report.json` is updated from sanitized report content only
- **AND THEN** raw session-specific absolute paths and timestamps are not committed into the snapshot

### Requirement: Demo-pack runner SHALL have explicit SKIP behavior for missing real-agent prerequisites
The demo-pack runner SHALL exit `0` with a `SKIP:` message when required real-agent prerequisites are unavailable, including at minimum:

- missing supported credentials for the selected tool lane
- `tmux` unavailable
- CAO unavailable or unreachable for the chosen demo path
- unsupported external CAO ownership for the first-version live path

The default supported live path for this pack SHALL be launcher-managed loopback CAO. The first version SHALL NOT guess ownership or shutdown responsibilities for arbitrary external CAO instances.

#### Scenario: Missing selected-tool credentials produces a SKIP result
- **WHEN** a maintainer runs the skill-invocation demo for one tool lane without the required credential profile material
- **THEN** the demo exits `0`
- **AND THEN** it prints a `SKIP:` message explaining that the selected real-agent prerequisites are missing

#### Scenario: Unsupported external CAO ownership is skipped
- **WHEN** a maintainer points the demo at a non-loopback or otherwise unsupported external CAO instance for the first-version live path
- **THEN** the demo exits `0`
- **AND THEN** it prints a `SKIP:` message explaining that the selected CAO ownership model is unsupported for this pack
