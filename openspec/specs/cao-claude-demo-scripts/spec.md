# cao-claude-demo-scripts Specification

## Purpose
TBD - created by archiving change cao-claude-demo-fs-interrupt. Update Purpose after archive.
## Requirements
### Requirement: Provide CAO-backed Claude demo packs

The repository SHALL provide two demo packs under `scripts/demo/` for CAO-managed Claude Code:

- `scripts/demo/cao-claude-tmp-write/`
- `scripts/demo/cao-claude-esc-interrupt/`

Each demo pack SHALL include:

- `README.md` documenting prerequisites, what the demo does, and how to run it
- `run_demo.sh` as the primary entrypoint
- `inputs/` containing prompt input files used by the demo
- `scripts/verify_report.py` to verify (and optionally snapshot) a sanitized `report.json`
- `expected_report/report.json` containing the sanitized expected report shape

#### Scenario: Demo pack layout is present
- **WHEN** a developer inspects `scripts/demo/`
- **THEN** the two demo pack directories and required files exist at the specified paths

### Requirement: Demo packs have safe, explicit SKIP behavior

Each demo pack `run_demo.sh` SHALL exit with status code `0` and print a line starting with `SKIP:` when a prerequisite is not met, including at least:

- missing credential profile inputs
- invalid/unauthorized credentials
- CAO connectivity unavailable
- `tmux` not available

Additionally, the demos that require local tmux + local filesystem effects (tmp
writes and `Esc` injection) SHALL SKIP unless `CAO_BASE_URL` is a supported
loopback CAO URL that uses `http`, host `localhost` or `127.0.0.1`, and an
explicit port.

#### Scenario: Remote CAO is skipped
- **WHEN** a developer runs the demo with `CAO_BASE_URL` set to a non-local URL
- **THEN** the demo exits `0` and prints `SKIP:` indicating local-only requirements

#### Scenario: Non-default loopback port is accepted
- **WHEN** a developer runs the demo with `CAO_BASE_URL=http://127.0.0.1:9991`
- **THEN** the demo treats that URL as satisfying the local-only CAO prerequisite
- **AND THEN** it does not skip solely because the loopback port is not `9889`

### Requirement: `cao-claude-tmp-write` creates and verifies a runnable code file under `tmp/`

The `scripts/demo/cao-claude-tmp-write/run_demo.sh` demo SHALL:

1. start a CAO-backed Claude Code runtime session,
2. prompt Claude Code to create a deterministic code file under a unique `tmp/<subdir>/...`,
3. verify the file exists and executes successfully, producing a sentinel output string, and
4. write a `report.json` that passes `scripts/verify_report.py`.

The demo SHALL avoid modifying tracked repository files (it may create new artifacts under `tmp/`).

#### Scenario: Running tmp-write demo produces sentinel output
- **WHEN** a developer runs `scripts/demo/cao-claude-tmp-write/run_demo.sh` with valid local CAO + credentials
- **THEN** the generated code file exists under `tmp/` and running it prints the expected sentinel output

### Requirement: `cao-claude-esc-interrupt` demonstrates interrupt + recovery

The `scripts/demo/cao-claude-esc-interrupt/run_demo.sh` demo SHALL:

1. start a CAO-backed Claude Code runtime session,
2. submit a “long-ish” prompt and confirm the terminal enters a `processing` state,
3. send a real `Esc` keystroke to the correct tmux target (`session_name:window_name`) to simulate user interruption,
4. verify the terminal returns to an idle prompt, and
5. submit a second prompt and verify a non-empty response is extracted, then write a `report.json` that passes `scripts/verify_report.py`.

The demo SHALL print debugging breadcrumbs including `terminal_id` and the CAO pipe log path `~/.aws/cli-agent-orchestrator/logs/terminal/<terminal_id>.log`.

#### Scenario: Interrupt mid-turn and recover
- **WHEN** a developer runs `scripts/demo/cao-claude-esc-interrupt/run_demo.sh` with valid local CAO + credentials
- **THEN** the demo sends `Esc`, the terminal returns to idle, and a second prompt completes with a non-empty extracted answer
