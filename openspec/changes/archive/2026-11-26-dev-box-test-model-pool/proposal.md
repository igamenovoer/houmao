# Proposal

## Why

Maintained instructional suites and developer agent tests currently hardcode host-specific model IDs, loopback ports, client executable paths, and DSH-only post-prepare reasoning commands directly inside tracked `README.md` workflows (`Qwen/Qwen3.8-27B-FP8`, `http://127.0.0.1:14888/v1`, `$REPO_ROOT/tmp/dsh/...`). Because available endpoints, credentials, and preferred models vary across developer machines and across roles in multi-agent tests, developers need an untracked dev-box model pool outside the checkout paired with environment-variable key selection so any single-agent or multi-agent test can pick homogeneous or per-role models without editing tracked test definitions.

## What Changes

- Introduce an external dev-box model pool file (`model-pool.toml`) stored outside the checkout at `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/model-pool.toml` (overridable via `HOUMAO_TEST_MODEL_POOL`) with owner-only permissions (`0600`). Each named pool key binds a client, auth or case mode (`self-hosted`, `cloud-api`, or `native-login`), non-secret routing and capacity metadata, optional local client `executable`, optional birth-time `reasoning_level`, and references to external `.env` files or imported `auth_bundle` names rather than inline API keys.
- Add deterministic environment-variable key resolution for logical test-agent slots: check `HOUMAO_TEST_MODEL_<SLOT>` first (for example `HOUMAO_TEST_MODEL_LEAD` or `HOUMAO_TEST_MODEL_A`), fall back to `HOUMAO_TEST_MODEL` for homogeneous runs, and fail fast with available pool keys listed when neither variable is set (never guessing ambient credentials or models).
- Extend `scripts/agents/test-fixtures/fixture.py` with `list-models` and `--pool-key` / `--pool-slot` / `--model-pool` options on `check` and `prepare`, validating requested run-mode compatibility (`web`, `service`, `headless`, `tui`) and recording sanitized `pool_key` and `pool_slot` metadata in `run.json`.
- Generalize manager-surface `--reasoning-level` support in `fixture.py prepare` beyond Kimi to supported manager clients (including DSH slot indices validated against declared `dsh_reasoning` slots) so pool entries can set birth-time reasoning presets without client-specific post-prepare `houmao-mgr project profile set` steps in test scripts.
- Add a secret-free tracked example template at `tests/fixtures/agent-launch/model-pool.example.toml` and update fixture documentation (`scripts/agents/test-fixtures/README.md`, `tests/fixtures/agent-launch/README.md`, and `AGENTS.md`).
- Update tracked instructional test bundles (`tests/instructional/agent-cccc-cuda-coop/`, `tests/instructional/agent-cccc/`, `tests/instructional/agent-mail-stalwart/`, and `tests/instructional/skill-update/`) to select per-agent models via `HOUMAO_TEST_MODEL_<SLOT>` / `HOUMAO_TEST_MODEL` instead of hardcoding `Qwen/Qwen3.8-27B-FP8`, `127.0.0.1:14888`, or checkout-local DSH binary paths.

## Capabilities

### New Capabilities
- `test-agent-model-pool`: External dev-box `model-pool.toml` schema, path and permission validation, `HOUMAO_TEST_MODEL_<SLOT>` / `HOUMAO_TEST_MODEL` resolution, `fixture.py list-models` and `--pool-key` / `--pool-slot` CLI integration, run-mode compatibility checks, and instructional-suite slot binding.

### Modified Capabilities
- `test-agent-launch-fixtures`: Generalize manager-surface birth-time `--reasoning-level` preparation across supported clients (including DSH alongside Kimi) and allow `check` and `prepare` to source explicit launch configuration and client executable paths from a selected model-pool entry while recording sanitized pool selection metadata.
- `agent-fixture-contracts`: Register the external dev-box `model-pool.toml` resource alongside the external `auth/` credential store and publish the secret-free tracked template `tests/fixtures/agent-launch/model-pool.example.toml`.

## Impact

- **Test fixture tooling (`utility`)**: `scripts/agents/test-fixtures/fixture.py` and `scripts/agents/test-fixtures/fixturelib/` (`pool.py`, `config.py`, `prepare.py`, `auth.py`).
- **Fixture templates and docs**: `tests/fixtures/agent-launch/model-pool.example.toml`, `tests/fixtures/agent-launch/README.md`, `scripts/agents/test-fixtures/README.md`, and `AGENTS.md`.
- **Instructional suites (`CI`)**: `tests/instructional/agent-cccc-cuda-coop/`, `tests/instructional/agent-cccc/`, `tests/instructional/agent-mail-stalwart/`, and `tests/instructional/skill-update/`.
- **Unit tests (`CI`)**: Hermetic unit coverage under `tests/unit/` for pool parsing, external-path enforcement, slot env precedence, mode compatibility errors, and DSH/Kimi manager `reasoning_level` preparation using synthetic files.
- **Core package (`distro`)**: Unchanged; `src/houmao/` requires no modifications.
