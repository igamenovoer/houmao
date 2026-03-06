## ADDED Requirements

### Requirement: Repository provides a CAO-backed Codex demo pack

The repository SHALL provide a CAO-backed Codex demo pack under `scripts/demo/cao-codex-session/` including at minimum:

- `README.md`
- `run_demo.sh`
- `inputs/`
- `scripts/verify_report.py`
- `expected_report/report.json`

#### Scenario: Codex demo pack layout is present
- **WHEN** a developer inspects `scripts/demo/cao-codex-session/`
- **THEN** the required files and directories are present

### Requirement: Codex CAO demo startup aligns launcher home and profile store

The Codex CAO demo SHALL align launcher home context and runtime profile installation path by passing an explicit profile-store path to session start that resolves under the launcher home context.

#### Scenario: Codex session start uses aligned profile-store path
- **WHEN** a developer runs `scripts/demo/cao-codex-session/run_demo.sh` with local prerequisites satisfied
- **THEN** the demo computes/uses a profile-store path under the launcher home context
- **AND THEN** `start-session` receives that explicit profile-store path

### Requirement: Codex CAO demo lifecycle uses launcher module entrypoints

The Codex CAO demo SHALL perform CAO server lifecycle control through `python -m gig_agents.cao.tools.cao_server_launcher` commands (`status`, `start`, `stop`) and launcher command outputs.

The demo SHALL NOT use direct process-discovery/signal logic to manage `cao-server` processes.

#### Scenario: Codex demo invokes launcher module for lifecycle control
- **WHEN** a developer runs `scripts/demo/cao-codex-session/run_demo.sh`
- **THEN** CAO server lifecycle operations are executed via launcher module CLI commands
- **AND THEN** demo control flow is driven by launcher outputs instead of ad-hoc OS process management

### Requirement: Codex CAO demo has explicit skip taxonomy

The Codex CAO demo runner SHALL classify `SKIP:` outcomes distinctly for at least:

- missing credential/profile input files,
- invalid/unauthorized credentials,
- CAO connectivity unavailable, and
- CAO profile-store mismatch during terminal creation (for example profile-load failures such as `Agent profile not found`).

#### Scenario: Profile-store mismatch is not mislabeled as missing credentials
- **WHEN** Codex CAO session start fails due to profile-load failure in CAO
- **THEN** the demo exits `0` with `SKIP:`
- **AND THEN** the skip reason identifies profile-store/context mismatch rather than missing credentials

### Requirement: Codex local-loopback startup avoids silent untracked-server reuse

For local loopback CAO demo runs, if launcher startup detects reuse of a healthy server that is not tracked by the current demo runtime context, the demo SHALL use launcher-driven control flow (for example launcher-mediated retry or explicit fail-fast) and SHALL surface explicit ownership/context diagnostics.

#### Scenario: Untracked healthy loopback server is handled deterministically
- **WHEN** the Codex CAO demo starts and an already-healthy loopback server exists outside the demo-managed context
- **THEN** the demo does not silently continue with unknown server ownership
- **AND THEN** the demo uses launcher-module lifecycle behavior rather than direct process signaling
- **AND THEN** the demo either re-establishes a managed local server context or exits with an explicit error message
