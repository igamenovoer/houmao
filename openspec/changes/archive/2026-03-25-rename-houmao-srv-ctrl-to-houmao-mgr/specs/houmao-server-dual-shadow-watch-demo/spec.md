## MODIFIED Requirements

### Requirement: Demo startup SHALL launch one Claude session, one Codex session, and one monitor session through the supported Houmao pair
The start flow SHALL launch:

- one Claude session through `houmao-mgr launch`,
- one Codex session through `houmao-mgr launch`, and
- one separate tmux monitor session.

For supported Claude and Codex sessions in this pack, the effective persisted Houmao session identity SHALL remain `houmao_server_rest` and the effective parsing posture SHALL remain `shadow_only`.

Startup SHALL persist structured state for the run, including at minimum the run root, the Houmao server base URL, the two session names, each terminal id, each tmux session name, and the monitor tmux session name.

Startup SHALL surface attach commands for the Claude session, the Codex session, and the monitor session so the operator can manually interact with both TUIs while watching the dashboard.

#### Scenario: Successful startup surfaces three live tmux sessions through the Houmao pair
- **WHEN** the operator runs the demo start command with prerequisites satisfied
- **THEN** the demo launches one Claude session and one Codex session through `houmao-mgr` against the demo-owned `houmao-server`
- **AND THEN** the resulting tracked sessions are registered in `houmao-server`
- **AND THEN** the demo starts a separate tmux session for the monitor dashboard
- **AND THEN** startup output includes attach commands for the Claude session, the Codex session, and the monitor session

#### Scenario: Startup persists Houmao-server-backed session identity
- **WHEN** the operator starts the Houmao-server dual shadow-watch demo
- **THEN** the persisted run state records the Houmao server base URL plus the launched session and terminal identities
- **AND THEN** follow-up demo commands treat `houmao-server` as the session authority instead of bypassing it through raw CAO control paths

### Requirement: README SHALL teach the Houmao-owned manual state-validation workflow
The demo-pack README SHALL document:

- prerequisites,
- the standalone purpose of the pack,
- the dummy-project workdir posture,
- the supported `houmao-server + houmao-mgr` pair boundary,
- the start, inspect, attach, and stop workflow,
- that the operator manually prompts the live Claude Code and Codex TUIs while watching server-tracked state change in the monitor,
- the meaning of the displayed parser, lifecycle, lifecycle-authority, stability, and timing fields, and
- concrete manual interactions the operator can perform to validate state changes.

The README SHALL make clear that `houmao-server` is the authoritative live tracking surface for what the monitor displays and that the demo is a server-state observation surface rather than a second parser or lifecycle tracker.

#### Scenario: Maintainer can follow the README to perform a Houmao-server-based manual validation run
- **WHEN** a maintainer follows the README from a fresh checkout with prerequisites satisfied
- **THEN** they can start the demo, attach to the Claude and Codex sessions, watch the monitor session, and stop the run without hidden setup steps
- **AND THEN** the README explains that `houmao-server` is the authoritative live tracking surface for what the monitor displays

#### Scenario: Maintainer understands the prompt-and-observe purpose from the README
- **WHEN** a maintainer reads the README before running the demo
- **THEN** they understand that the intended workflow is to interactively prompt the live TUIs and observe how `houmao-server` tracked state changes
- **AND THEN** the README does not imply that the demo itself is the primary owner of parser, lifecycle, or state-tracking semantics
