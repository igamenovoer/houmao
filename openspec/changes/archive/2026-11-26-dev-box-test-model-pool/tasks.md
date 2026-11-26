# Tasks

## 1. External Model Pool Schema and Slot Resolver

- [x] 1.1 Implement `scripts/agents/test-fixtures/fixturelib/pool.py` for external `model-pool.toml` path resolution (`--model-pool`, `HOUMAO_TEST_MODEL_POOL`, and XDG default `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/model-pool.toml`), checkout/symlink/`0600` permission checks, secret-free Pydantic entry validation (`self-hosted`, `cloud-api`, and `native-login`), and `HOUMAO_TEST_MODEL_<SLOT>` / `HOUMAO_TEST_MODEL` lookup, and verify `pixi run ruff check scripts/agents/test-fixtures/fixturelib/pool.py` exits zero.
- [x] 1.2 Add hermetic unit tests in `tests/unit/agents/test_model_pool_fixture.py` covering XDG path resolution, checkout-resident and permissive-mode rejections, inline-secret schema rejection, slot environment precedence, and missing-variable error messages listing valid keys, and verify `pixi run pytest tests/unit/agents/test_model_pool_fixture.py` passes.
- [x] 1.3 Author the secret-free template `tests/fixtures/agent-launch/model-pool.example.toml` and update `tests/fixtures/agent-launch/README.md` with external dev-box pool instructions, and verify a unit test in `tests/unit/agents/test_model_pool_fixture.py` parses `model-pool.example.toml` cleanly without live credentials.

## 2. Fixture CLI Integration and Manager Reasoning Levels

- [x] 2.1 Generalize manager-surface `--reasoning-level` validation in `scripts/agents/test-fixtures/fixturelib/config.py` so DSH `dsh_reasoning` slot maps and Kimi `support_efforts` both create `fixture-agent` launch profiles with validated preset indices while rejecting out-of-range or non-manager combinations, and verify unit tests pass in `tests/unit/agents/test_dsh_web_fixture_tools.py` and `tests/unit/agents/test_agent_fixture_tools.py`.
- [x] 2.2 Add `list-models` and `--pool-key` / `--pool-slot` / `--model-pool` support to `scripts/agents/test-fixtures/fixture.py` and `scripts/agents/test-fixtures/fixturelib/prepare.py` (enforcing flag mutual exclusion, checking `--mode`/`--surface` compatibility, applying pool `executable`, and writing sanitized `pool_key` and `pool_slot` metadata to `run.json`), and verify CLI unit tests pass in `tests/unit/agents/test_model_pool_fixture.py`.
- [x] 2.3 Update `scripts/agents/test-fixtures/README.md` and `AGENTS.md` to document `model-pool.toml`, `list-models`, `--pool-key`, `--pool-slot`, and generalized manager `--reasoning-level`, and verify `pixi run python scripts/agents/test-fixtures/fixture.py --help` and `pixi run python scripts/agents/test-fixtures/fixture.py list-models --help` match the documented options.

## 3. Instructional Suite Migration to Slot-Based Model Selection

- [x] 3.1 Update `tests/instructional/agent-cccc-cuda-coop/` (`manifest.toml`, `helpers/cuda_coop_lab.py`, `README.md`, and `cases/*.md`) to declare `[team.slots.<role>]`, check and prepare all four roles via `fixture.py` `--pool-slot <role> --mode web --surface manager`, and record per-role `pool_key` provenance in `run-meta.json` and `doctor` output, and verify `cuda_coop_lab.py show-manifest` and `pixi run ruff check tests/instructional/agent-cccc-cuda-coop/helpers/cuda_coop_lab.py` pass.
- [x] 3.2 Update the `Launch` sections of `tests/instructional/agent-cccc/README.md`, `tests/instructional/agent-mail-stalwart/README.md`, and `tests/instructional/skill-update/README.md` (preserving historical `Self-Proof` records) to prepare agents via `fixture.py` `--pool-slot` instead of hardcoded `MODEL`, `BASE_URL`, `DSH_EXECUTABLE`, and manual `profile set --reasoning-level 3` calls, add a guard in `tests/unit/docs/test_agent_fixture_consumers.py` checking instructional `Launch` sections against hardcoded loopback endpoints or checkout-local DSH binaries, and verify `pixi run pytest tests/unit/docs/test_agent_fixture_consumers.py` passes.

## 4. Cross-Suite Verification

- [x] 4.1 Run `pixi run format --check`, `pixi run lint`, `pixi run typecheck`, and `pixi run test` across the repository and confirm all checks exit zero with no changes under `src/houmao/`.

## Workflow follow-up

- Archive `dev-box-test-model-pool` after implementation verification and review are complete.
- Sync delta specifications into `openspec/specs/` during archive and verify the archived state.
