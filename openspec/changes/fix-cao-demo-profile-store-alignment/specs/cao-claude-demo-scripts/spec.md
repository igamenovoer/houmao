## MODIFIED Requirements

### Requirement: Demo packs have safe, explicit SKIP behavior

Each demo pack `run_demo.sh` SHALL exit with status code `0` and print a line starting with `SKIP:` when a prerequisite is not met, including at least:

- missing credential profile inputs
- invalid/unauthorized credentials
- CAO connectivity unavailable
- `tmux` not available
- CAO profile-store mismatch during terminal creation (for example profile-load failures such as `Agent profile not found`)

Additionally, the demos that require local tmux + local filesystem effects (tmp writes and `Esc` injection) SHALL SKIP unless `CAO_BASE_URL` is a local URL (at minimum `http://localhost:9889` or `http://127.0.0.1:9889`).

#### Scenario: Remote CAO is skipped
- **WHEN** a developer runs the demo with `CAO_BASE_URL` set to a non-local URL
- **THEN** the demo exits `0` and prints `SKIP:` indicating local-only requirements

#### Scenario: Profile-store mismatch is classified explicitly
- **WHEN** demo session start fails because CAO cannot load the runtime-generated profile (for example `Agent profile not found`)
- **THEN** the demo exits `0` with `SKIP:`
- **AND THEN** the message indicates profile-store/context mismatch rather than missing credential inputs

## ADDED Requirements

### Requirement: Claude CAO demo lifecycle uses launcher module entrypoints

For `scripts/demo/cao-claude-tmp-write/` and `scripts/demo/cao-claude-esc-interrupt/`, CAO server lifecycle control SHALL be performed through `python -m gig_agents.cao.tools.cao_server_launcher` commands (`status`, `start`, `stop`) and launcher command outputs.

Demo scripts SHALL NOT use direct process-discovery/signal logic to manage `cao-server` processes.

#### Scenario: Claude demos invoke launcher module for lifecycle control
- **WHEN** a developer runs either Claude CAO demo
- **THEN** CAO server lifecycle operations are executed via launcher module CLI commands
- **AND THEN** demo control flow is driven by launcher outputs instead of ad-hoc OS process management

### Requirement: Claude CAO demo startup aligns launcher home and profile store

For `scripts/demo/cao-claude-tmp-write/` and `scripts/demo/cao-claude-esc-interrupt/`, demo startup SHALL align CAO launcher home context and runtime profile installation path by passing an explicit profile-store path to session start that resolves under the launcher home context.

#### Scenario: Session start uses aligned profile-store path
- **WHEN** a developer runs either Claude CAO demo with local prerequisites satisfied
- **THEN** the demo computes/uses a profile-store path under the launcher home context
- **AND THEN** `start-session` receives that explicit profile-store path

### Requirement: Claude local-loopback demo startup avoids silent untracked-server reuse

For local loopback CAO demo runs, if launcher startup detects reuse of a healthy server that is not tracked by the current demo runtime context, the demo SHALL use launcher-driven control flow (for example launcher-mediated retry or explicit fail-fast) and SHALL surface explicit ownership/context diagnostics.

#### Scenario: Untracked healthy loopback server is handled deterministically
- **WHEN** a local Claude CAO demo starts and an already-healthy loopback server exists outside the demo-managed context
- **THEN** the demo does not silently continue with unknown server ownership
- **AND THEN** the demo uses launcher-module lifecycle behavior rather than direct process signaling
- **AND THEN** the demo either re-establishes a managed local server context or exits with an explicit error message
