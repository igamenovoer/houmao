## ADDED Requirements

### Requirement: Launcher stop SHALL persist structured diagnostics from a fresh runtime root
The launcher SHALL ensure the parent directory for `launcher_result.json` exists before writing structured `stop` results under `runtime_root/cao-server/<host>-<port>/`.

This requirement SHALL apply even when `stop` returns early because no pidfile exists, because the tracked pid is stale, or because process verification fails.

The launcher SHALL return a structured `stop` result payload instead of raising a filesystem error solely because the runtime artifact directory did not exist before the `stop` command began.

#### Scenario: Stop without a preexisting artifact directory returns structured already-stopped output
- **WHEN** a developer runs launcher `stop` for `http://127.0.0.1:9889`
- **AND WHEN** the resolved `runtime_root/cao-server/127.0.0.1-9889/` directory does not yet exist
- **AND WHEN** no pidfile exists for that config
- **THEN** the launcher returns a structured `already_stopped` result payload
- **AND THEN** it writes `launcher_result.json` under the resolved artifact directory
- **AND THEN** it does not fail solely because the artifact directory was missing before the command
