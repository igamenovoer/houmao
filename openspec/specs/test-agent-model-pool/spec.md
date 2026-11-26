# test-agent-model-pool Specification

## Purpose

Define an untracked, owner-private dev-box model pool outside the repository checkout and deterministic environment-variable key selection so test harnesses and instructional suites bind per-agent models without hardcoding machine-specific endpoints, model IDs, or client binaries in tracked files.

## Requirements

### Requirement: Model pool resides outside the checkout with owner-only permissions

The test fixture system SHALL resolve the dev-box model pool file from an explicit CLI path, `HOUMAO_TEST_MODEL_POOL`, or `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/model-pool.toml` by default. Resolution SHALL reject any path inside the repository checkout (including `tmp/` and symlinks) or shared roots (`/`, `/tmp`, `$HOME`), and SHALL reject symlinked or non-owner-private pool files.

#### Scenario: Default pool path resolves to external XDG storage
- **WHEN** neither `--model-pool` nor `HOUMAO_TEST_MODEL_POOL` is supplied
- **THEN** the helper resolves `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/model-pool.toml` outside the checkout

#### Scenario: Checkout-resident pool path is rejected
- **WHEN** `--model-pool` or `HOUMAO_TEST_MODEL_POOL` points inside the repository checkout or its `tmp/` directory
- **THEN** validation fails before reading or preparing any run state

### Requirement: Model pool entries store non-secret routing and credential file references

Each `[models.<key>]` entry in `model-pool.toml` SHALL declare `schema_version = 1` at the file root and specify client, authentication/case routing (`self-hosted`, `cloud-api`, or `native-login`), model metadata, optional client `executable`, and optional birth-time `reasoning_level`. Pool entries SHALL reference external `.env` files or imported `auth_bundle` names and SHALL reject inline raw API keys or credential tokens.

#### Scenario: Pool entry with inline secret field is rejected
- **WHEN** a `model-pool.toml` entry contains an `api_key`, `auth_token`, or credential-bearing URL
- **THEN** pool loading fails with a schema error without echoing the secret value

#### Scenario: Pool entry binds cloud credentials by external env file
- **WHEN** a `cloud-api` pool entry specifies an external `env_file` outside the checkout
- **THEN** preparation reads credentials from that `env_file` and keeps `model-pool.toml` secret-free

### Requirement: Logical agent slots resolve pool keys deterministically from environment variables

When preparing or checking a logical agent slot `<slot>`, the helper SHALL normalize `<slot>` to uppercase `[A-Z0-9_]+`, check `HOUMAO_TEST_MODEL_<SLOT>` first, and fall back to `HOUMAO_TEST_MODEL`. When neither variable is set or the selected key is absent from `model-pool.toml`, resolution SHALL fail explicitly and list available pool keys without guessing ambient credentials or models.

#### Scenario: Per-slot variable overrides global model variable
- **WHEN** `HOUMAO_TEST_MODEL=qwen_local` and `HOUMAO_TEST_MODEL_ALGO=deepseek_cloud` are both set
- **THEN** slot `algo` selects `deepseek_cloud` while slot `lead` selects `qwen_local`

#### Scenario: Missing model environment variable fails with available keys
- **WHEN** a slot resolution runs with neither `HOUMAO_TEST_MODEL_<SLOT>` nor `HOUMAO_TEST_MODEL` set
- **THEN** the helper exits non-zero, names the expected environment variables, and lists valid keys from `model-pool.toml`

### Requirement: Fixture CLI lists pool entries and validates run-mode compatibility

The test fixture CLI SHALL expose `list-models` to emit secret-free JSON summaries of configured pool keys, and SHALL accept `--pool-key` or `--pool-slot` (mutually exclusive with conflicting raw routing flags) on `check` and `prepare`. If the caller requests a `--mode` or `--surface` unsupported by the selected pool entry's client or declared `supported_modes`, validation SHALL fail before creating run directories.

#### Scenario: Listing configured pool entries hides credential paths and secrets
- **WHEN** a developer runs `fixture.py list-models` against a valid `model-pool.toml`
- **THEN** the output lists each pool key, client, case or auth method, model ID, and supported modes without secret values

#### Scenario: Incompatible run mode is rejected before preparation
- **WHEN** an instructional test requires `--mode web` and the selected pool key resolves to a client or entry that does not support `web`
- **THEN** `check` and `prepare` fail immediately with an actionable mode-compatibility error

### Requirement: Prepared runs record sanitized pool provenance

When `fixture.py prepare` resolves configuration from a pool entry, the resulting `run.json` SHALL record `pool_key` (and `pool_slot` when selected by slot) alongside the existing secret-free configuration summary, and SHALL apply the pool entry's `executable` unless overridden on the command line.

#### Scenario: Prepared run metadata records pool key and slot
- **WHEN** `fixture.py prepare --pool-slot lead` succeeds for `HOUMAO_TEST_MODEL_LEAD=qwen_local`
- **THEN** `run.json` records `pool_key: "qwen_local"` and `pool_slot: "lead"` without storing credential values or private file paths

### Requirement: Tracked instructional suites select agent models via slot environment variables

Maintained instructional test bundles under `tests/instructional/` SHALL prepare managed test agents through `fixture.py` pool-slot or pool-key selection (`HOUMAO_TEST_MODEL_<SLOT>` / `HOUMAO_TEST_MODEL`) and SHALL NOT hardcode dev-box-specific model names, loopback model URLs, checkout-local client binaries, or DSH-only post-prepare reasoning commands in tracked `README.md` or helper scripts.

#### Scenario: Homogeneous four-agent CUDA cooperation run uses one environment variable
- **WHEN** an operator sets `HOUMAO_TEST_MODEL` to a valid Web-capable pool key and runs `tests/instructional/agent-cccc-cuda-coop/`
- **THEN** all four agents (`lead`, `algo`, `kernel`, `profiler`) prepare and launch using that pool entry without editing tracked files

#### Scenario: Mixed-model multi-agent run overrides individual roles
- **WHEN** an operator sets `HOUMAO_TEST_MODEL` plus one or more `HOUMAO_TEST_MODEL_<ROLE>` overrides
- **THEN** each role prepares with its resolved pool entry and `run-meta.json` records the per-role pool provenance
