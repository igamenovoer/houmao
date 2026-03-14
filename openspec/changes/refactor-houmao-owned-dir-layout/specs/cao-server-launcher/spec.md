## ADDED Requirements

### Requirement: Launcher defaults CAO home under the per-server runtime subtree
The launcher SHALL treat CAO `HOME` as launcher-owned mutable service state that is distinct from the shared registry root and from agent workdirs.

When launcher config and CLI overrides do not provide an explicit `runtime_root`, and `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to an absolute directory path, the launcher SHALL use that env-var value as the effective runtime root before deriving launcher artifacts or default `home_dir`.

When launcher config does not provide an explicit `home_dir`, the launcher SHALL derive a default CAO home for that base URL under the effective runtime root as:
- `<runtime_root>/cao_servers/<host>-<port>/home/`

When launcher config provides an explicit `home_dir`, the launcher SHALL use that explicit path instead of the derived default.

The effective CAO home SHALL remain writable because CAO writes its own state there.

#### Scenario: Launcher start derives a default CAO home from the runtime root
- **WHEN** the launcher starts `cao-server` for base URL `http://localhost:9889`
- **AND WHEN** launcher config omits `home_dir`
- **THEN** the launcher uses `<runtime_root>/cao_servers/localhost-9889/home/` as the effective CAO `HOME`

#### Scenario: Explicit home_dir override is preserved
- **WHEN** the launcher starts `cao-server` for base URL `http://localhost:9889`
- **AND WHEN** launcher config explicitly provides `home_dir = "/data/custom/cao-home"`
- **THEN** the launcher uses `/data/custom/cao-home` as the effective CAO `HOME`
- **AND THEN** it does not replace that explicit path with the derived default

#### Scenario: Runtime-root env-var override relocates launcher artifacts and default home
- **WHEN** `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to `/tmp/houmao-runtime`
- **AND WHEN** launcher config and CLI overrides do not provide an explicit `runtime_root`
- **AND WHEN** launcher config omits `home_dir`
- **THEN** the launcher uses `/tmp/houmao-runtime` as the effective runtime root
- **AND THEN** it derives the default CAO `HOME` under `/tmp/houmao-runtime/cao_servers/<host>-<port>/home/`

## MODIFIED Requirements

### Requirement: Launcher writes pid and log artifacts under the runtime root
When the launcher starts a `cao-server` process, it SHALL persist service artifacts under a deterministic path rooted at the configured runtime root.

The launcher SHALL record at least:
- a pid file containing the started process pid,
- a server log file capturing stdout/stderr, and
- a structured ownership artifact describing the standalone service context.

The launcher SHALL partition artifacts by base URL host/port under a launcher-specific subtree:
`runtime_root/cao_servers/<host>-<port>/launcher/`.

The launcher SHOULD additionally write a structured diagnostics file (for example `launcher_result.json`) in the same launcher-specific directory to simplify debugging.

#### Scenario: Start writes pid, log, and ownership artifacts in the launcher subtree
- **WHEN** the launcher starts a local `cao-server` process at base URL `http://localhost:9889`
- **THEN** it writes `runtime_root/cao_servers/localhost-9889/launcher/cao-server.pid`
- **AND THEN** it writes `runtime_root/cao_servers/localhost-9889/launcher/cao-server.log`
- **AND THEN** it writes a structured ownership artifact in `runtime_root/cao_servers/localhost-9889/launcher/`
- **AND THEN** the launcher reports the pid and artifact paths in its result payload

### Requirement: Launcher stop SHALL persist structured diagnostics from a fresh runtime root
The launcher SHALL ensure the parent directory for `launcher_result.json` exists before writing structured `stop` results under `runtime_root/cao_servers/<host>-<port>/launcher/`.

This requirement SHALL apply even when `stop` returns early because no pidfile exists, because the tracked pid is stale, or because process verification fails.

The launcher SHALL return a structured `stop` result payload instead of raising a filesystem error solely because the runtime artifact directory did not exist before the `stop` command began.

#### Scenario: Stop without a preexisting artifact directory returns structured already-stopped output
- **WHEN** a developer runs launcher `stop` for `http://127.0.0.1:9889`
- **AND WHEN** the resolved `runtime_root/cao_servers/127.0.0.1-9889/launcher/` directory does not yet exist
- **AND WHEN** no pidfile exists for that config
- **THEN** the launcher returns a structured `already_stopped` result payload
- **AND THEN** it writes `launcher_result.json` under the resolved launcher artifact directory
- **AND THEN** it does not fail solely because the artifact directory was missing before the command
