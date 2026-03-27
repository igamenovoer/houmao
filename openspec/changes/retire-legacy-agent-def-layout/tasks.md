## 1. Retire pack-local legacy agent trees

- [ ] 1.1 Update `scripts/demo/houmao-server-agent-api-demo-pack/agents/` to keep only canonical `roles/`, `tools/`, and any explicitly needed compatibility metadata, and remove tracked `brains/` / `blueprints/` assets plus stale README guidance.
- [ ] 1.2 Update `scripts/demo/passive-server-parallel-validation-demo-pack/agents/` to keep only canonical `roles/`, `tools/`, and any explicitly needed compatibility metadata, and remove tracked `brains/` / `blueprints/` assets plus stale README guidance.
- [ ] 1.3 Adjust the two server-demo provisioning and preflight paths so they resolve pack-owned presets, setups, adapters, and auth bundles from the canonical layout only.

## 2. Refactor launch consumers onto canonical preset/setup/auth paths

- [ ] 2.1 Migrate interactive-watch and related shared tracking helpers that still hardcode `tests/fixtures/agents/brains/...` to canonical preset-backed fixture inputs under `roles/` and `tools/`.
- [ ] 2.2 Migrate demo/tutorial helpers and shell scripts that still hardcode `brains/api-creds`, `brains/cli-configs`, `brains/brain-recipes`, or `blueprints/` so they resolve canonical `tools/<tool>/auth/`, `tools/<tool>/setups/`, and `roles/<role>/presets/` paths instead.
- [ ] 2.3 Keep any remaining compatibility-shaped metadata fields or helper parameters pointing at canonical preset-backed values and document those compatibility-only semantics where needed.

## 3. Migrate tracked fixtures and automated tests

- [ ] 3.1 Update `tests/fixtures/agents/` so tracked reusable assets live under canonical `skills/`, `roles/`, `tools/`, and optional compatibility metadata directories rather than legacy mirrors.
- [ ] 3.2 Refactor unit, integration, and demo tests that seed, assert, or fake legacy `brains/` / `blueprints/` paths so they use canonical preset/setup/auth layout or compatibility-only preset semantics.
- [ ] 3.3 Refresh tracked snapshots, canned reports, and fixture documentation whose expected path strings change because of the canonical-layout migration.

## 4. Refresh documentation and verify the migration

- [ ] 4.1 Update getting-started guides, fixture READMEs, demo-pack READMEs, and helper/operator docs so they describe only the canonical preset/setup/auth layout as current behavior.
- [ ] 4.2 Run targeted searches and regression coverage for the touched demos, helpers, and tests, confirming the changed scope no longer requires old-style `brains/` or `blueprints/` directories as authoritative launch inputs.
