## 1. CAO Server Launcher Core

- [x] 1.1 Add `src/agent_system_dissect/cao/server_launcher.py` with typed config/result models for `status`/`start`/`stop`
- [x] 1.2 Implement `status_cao_server(...)` (CAO health check via `GET /health`) with a configurable timeout
- [x] 1.3 Define and implement a minimal launcher config file format (recommend TOML) including: `base_url`, `runtime_root`, `home_dir` (CAO server `HOME`), `proxy_policy`, and startup timeout; config load is schema-validated (unknown keys rejected, actionable error messages); restrict `base_url` to upstream-supported values (`http://localhost:9889` and `http://127.0.0.1:9889`) until CAO host/port configurability is confirmed
- [x] 1.4 Implement proxy policy handling (`clear` vs `inherit`) for the launched `cao-server` process env:
  controlled vars: `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and lowercase equivalents; merge `NO_PROXY/no_proxy` to include `localhost,127.0.0.1,::1` non-destructively
- [x] 1.5 Implement CAO home handling for the launched server (`HOME` override) with fast-fail validation (absolute path, exists; document/validate writability expectations)
- [x] 1.6 Implement runtime artifact layout per base URL: `runtime_root/cao-server/<host>-<port>/` (`cao-server.pid`, `cao-server.log`, optional `launcher_result.json`)
- [x] 1.7 Implement `start_cao_server(...)`: invoke `cao-server` from `PATH` (no vendored `extern/orphan` usage); reuse an already-healthy server at `base_url` (do not start a second process); if starting, write pid/log artifacts and wait until healthy or timeout
- [x] 1.8 Implement `stop_cao_server(...)`: read pidfile from the `<host>-<port>` artifact directory; perform best-effort identity verification before killing (avoid blind kill on pid reuse); SIGTERM, wait up to 10s, then SIGKILL as fallback

## 2. User-Facing CLI Helper

- [x] 2.1 Add a small CLI entrypoint (for example `python -m agent_system_dissect.cao.tools.cao_server_launcher`) with `start`, `status`, and `stop` subcommands
- [x] 2.2 CLI reads a server config file (required) and optionally supports narrow flag overrides for ad-hoc use
- [x] 2.3 Add structured (JSON) output for `start/status/stop` so scripts can consume pid/log/base-url/health results

## 3. Tests

- [x] 3.1 Add unit tests for proxy env sanitization and `NO_PROXY/no_proxy` merge behavior (clear vs inherit)
- [x] 3.2 Add unit tests for runtime artifact path partitioning (`<host>-<port>`) and pidfile read/write behavior
- [x] 3.3 Add unit tests for config schema validation (unknown keys rejected; invalid enum values rejected; unsupported `base_url` rejected)
- [x] 3.4 Add unit tests for stop verification logic (refuse to kill if identity cannot be verified)
- [x] 3.5 Add an opt-in manual/integration test recipe (under `tests/manual/` or docs) that proves `/data/...` workdir works when CAO `HOME` is configured to include the repo (and CAO state is written under that `HOME`)

## 4. Docs and Script Updates

- [x] 4.1 Document the launcher CLI + config format in `docs/` (including `uv` installation expectations: `cao-server` must be on `PATH`)
- [x] 4.2 Document CAO home/workdir/state contracts and recommended directory layouts (CAO state under `HOME/.aws/cli-agent-orchestrator/`; `working_directory` must be within `HOME`; read-only repos require writable CAO `HOME`)
- [x] 4.3 (Optional) Refactor `scripts/demo/*` CAO demos to reuse the shared launcher instead of duplicating `cao-server` startup logic
- [x] 4.4 Add repo-tracked example config(s) under `config/cao-server-launcher/` (for example `local.toml`) and reference them from docs and scripts
