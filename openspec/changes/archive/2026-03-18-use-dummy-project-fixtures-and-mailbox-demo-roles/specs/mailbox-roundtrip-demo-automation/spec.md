## MODIFIED Requirements

### Requirement: Mailbox roundtrip demo SHALL expose pack-local automation commands
The mailbox roundtrip tutorial pack SHALL expose pack-local automation through `run_demo.sh` plus helper-owned scripts under `scripts/demo/mailbox-roundtrip-tutorial-pack/`.

The wrapper SHALL support command-style entrypoints for `auto`, `start`, `roundtrip`, `inspect`, `verify`, and `stop`.

The default invocation MAY remain equivalent to `auto`, but the reusable command entrypoints SHALL still be available for maintainer-driven automation.

#### Scenario: Maintainer can discover automation entrypoints in the pack directory
- **WHEN** a maintainer inspects `scripts/demo/mailbox-roundtrip-tutorial-pack/`
- **THEN** the automation entrypoints and helper scripts live inside that pack directory
- **AND THEN** the pack documentation identifies those entrypoints as the supported mailbox-demo automation surface

#### Scenario: Wrapper accepts stepwise automation commands
- **WHEN** a maintainer invokes `run_demo.sh start`, `run_demo.sh roundtrip`, `run_demo.sh inspect`, `run_demo.sh verify`, or `run_demo.sh stop`
- **THEN** the wrapper routes to the corresponding pack-owned automation implementation
- **AND THEN** the caller does not need an external test-only orchestration layer to drive those phases

### Requirement: Stepwise automation SHALL reuse one selected demo output directory
The mailbox roundtrip demo automation commands SHALL operate against one caller-selected demo output directory and SHALL preserve the demo-local worktree, mailbox root, runtime root, and reusable state needed between commands.

`start` SHALL prepare or validate the selected demo output directory and SHALL start the live resources needed for a later `roundtrip`.

`roundtrip` SHALL reuse that same prepared demo output directory rather than provisioning an unrelated second workspace.

`inspect`, `verify`, and `stop` SHALL also operate against that same selected demo output directory.

#### Scenario: Start then inspect then roundtrip reuse the same demo root
- **WHEN** a maintainer runs `run_demo.sh start --demo-output-dir <path>`, then `run_demo.sh inspect --demo-output-dir <path> --agent sender`, and later `run_demo.sh roundtrip --demo-output-dir <path>`
- **THEN** all three commands operate on the same nested `project/`, `runtime/`, and `shared-mailbox/` layout under `<path>`
- **AND THEN** the inspect and roundtrip steps reuse the persisted demo-local state prepared for that same path

#### Scenario: Verify reuses existing demo outputs
- **WHEN** a maintainer runs `run_demo.sh verify --demo-output-dir <path>` after a successful stepwise or automatic run
- **THEN** verification builds or compares report artifacts from the existing demo outputs at `<path>`
- **AND THEN** it does not require a second unrelated one-shot demo run

## ADDED Requirements

### Requirement: Pack-local inspect SHALL expose stable per-agent watch coordinates
The mailbox roundtrip tutorial pack SHALL provide `run_demo.sh inspect --agent <sender|receiver>` as a pack-local watch surface for the two tutorial sessions.

By default, `inspect` SHALL render a human-readable summary for the selected agent. With `--json`, it SHALL emit a stable JSON object for that same selected agent.

For the selected agent, the inspect surface SHALL include at minimum:

- `agent_identity`,
- `session_name`,
- `tool`,
- `tool_state`,
- `tmux_target`,
- `tmux_attach_command`,
- `terminal_id`,
- `terminal_log_path`,
- `terminal_log_tail_command`,
- `project_workdir`,
- `runtime_root`, and
- `updated_at`.

When `--with-output-text <num-tail-chars>` is requested, `inspect` SHALL attempt to include the last `<num-tail-chars>` characters of best-effort projected dialog text for the selected agent and SHALL report explicit unavailability rather than failing the whole command if that live output tail cannot be produced.

If the live CAO terminal state cannot be resolved, `inspect` SHALL still render the persisted metadata and SHALL use `tool_state = unknown`.

#### Scenario: JSON inspect exposes attach and log coordinates for one participant
- **WHEN** a maintainer runs `run_demo.sh inspect --demo-output-dir <path> --agent receiver --json` after `start`
- **THEN** the JSON payload includes the selected receiver session's tmux attach command, terminal log path, terminal identifier, current tool state, and project/runtime paths
- **AND THEN** the payload uses the persisted receiver session identity instead of requiring the maintainer to reconstruct it manually

#### Scenario: Inspect tolerates unavailable live state
- **WHEN** a maintainer runs `inspect` for a selected tutorial agent after the CAO server is unavailable or the live terminal can no longer be queried
- **THEN** the command still prints the persisted tmux, terminal-log, and path metadata for that agent
- **AND THEN** it surfaces `tool_state` as `unknown`
- **AND THEN** it does not fail merely because live state lookup is unavailable
