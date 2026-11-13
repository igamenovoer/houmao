# Tasks

## 1. Generic Case Configuration

- [x] 1.1 Add the versioned `self-hosted` and `cloud-api` descriptors under `tests/fixtures/agent-launch/` and configuration resolution in `scripts/agents/test-fixtures/`; verify schema tests reject unknown fields, fixed personal defaults, and missing selected inputs while accepting arbitrary explicit model/endpoint values.
- [x] 1.2 Implement explicit process/env-file reference resolution with documented precedence and literal env parsing; verify synthetic tests cover quoted values, absent/empty keys, anonymous self-hosted credentials, required cloud keys, and non-execution/redaction of unsupported shell syntax.
- [x] 1.3 Implement client protocol/base-path selection and explicit model metadata validation; verify Claude Messages, Codex Responses, and Kimi Chat Completions mappings, unsupported protocol errors, nonduplicated version paths, and missing required model/capability diagnostics.
- [x] 1.4 Document case fields, the existing DeepSeek variable references, explicit model selection, and invocation examples in the fixture README/env example; verify examples resolve with synthetic values and include no real keys or Qwen/H20 defaults.

## 2. External Auth Storage and Discovery

- [x] 2.1 Implement XDG/default and explicit auth/run root resolution with private permissions and unique run IDs; verify tests reject checkout-contained roots and symlink escapes and isolate concurrent preparations outside the repository.
- [x] 2.2 Add read-only `discover-auth` for Claude, Codex, and Kimi configured/default homes plus explicit bounded search roots; verify synthetic-home tests cover supported files, companions, canonical deduplication, malformed/empty state, unsupported auth kinds, escaping symlinks, and secret-free candidate output.
- [x] 2.3 Add selected `import-auth` with staged atomic copies, opaque JSON preservation, duplicate protection, and explicit replacement; verify source bytes/metadata remain unchanged and only supported files enter user-private external bundles.
- [x] 2.4 Keep explicit native-login selection separate from API case resolution; verify API preparation works without auth JSON, never imports ambient login as a fallback, and native preparation preserves selected provider routing without injecting DeepSeek settings.
- [x] 2.5 Document local discovery/import, supported file shapes, candidate selection, replacement, and importability limitations in the helper/credential guidance; verify the documented synthetic import flow completes without copying a full home or creating repository-local credential files.

## 3. Current Client Setups and Isolated Homes

- [x] 3.1 Replace fixed Yunwu fixture setup/preset variants with generic `api-compatible` Codex assets and remove personal auth defaults from reusable plain presets; verify current preset/build tests and the required GPU-role variant inventory resolve with explicit runtime credentials.
- [x] 3.2 Align required plain-fixture and project-starter adapter projection settings with supported client inputs; verify builder tests show selected auth values reach the correct channel and credential-owned env remains separate from persistent specialist env records.
- [x] 3.3 Implement private native-home/setup rendering and run-local credential copies from normalized configuration; verify generated Codex routing matches the selected endpoint with no inline key, fresh homes exclude history, competing ambient bindings cannot change the selected backend, and simulated client writes cannot mutate reusable/source credentials.
- [x] 3.4 Implement qualified model metadata/context/reasoning projection where clients require it and update setup READMEs; verify arbitrary explicit model selection, actionable missing-metadata errors, and no inherited Qwen context, reasoning, or image assumptions in generated homes.

## 4. Preparation and Maintained Launch Surfaces

- [x] 4.1 Add managed project preparation through existing project/tool/credential/specialist behavior, using in-process secret-bearing credential commands; verify integration tests inspect real temporary catalog projections and ensure keys appear in neither OS arguments, captured command traces, manifests, nor returned metadata.
- [x] 4.2 Add `prepare`/`launch` execution for raw and manager surfaces in headless and unattended TUI modes; verify controlled client/subprocess tests confirm normalized-input parity, authoritative managed identities, Kimi flag compatibility, and selected effective environment across tmux boundaries.
- [x] 4.3 Support the maintained passive-server headless launch/turn surface without inventing passive TUI birth; verify controlled HTTP integration covers accepted headless creation, unsupported surface/mode preflight, and preserved selected configuration.
- [x] 4.4 Add offline-first `check`, sanitized run/report output, and identity-scoped failure cleanup; verify missing prerequisites remain explicit, failed launch state is inspectable, separate runs do not overwrite evidence, and cleanup affects only captured run-owned processes/sessions.
- [x] 4.5 Document prepare/launch/check, explicit live selection, external private outputs, raw/managed distinctions, and scoped follow-up commands; verify the documented controlled workflow runs through current supported command/API surfaces.

## 5. Existing Fixture Consumers and Guidance

- [x] 5.1 Migrate the minimal launch demo to selected generic cases, external private state, and current project/scoped CLI behavior; update its tutorial and contract tests, then verify controlled Claude/Codex TUI/headless runs preserve role/transport outputs without repository-local auth symlinks or retired root commands.
- [x] 5.2 Replace the packaged shared TUI demo's fixed auth lookup/symlink in `agent_assets.py` with explicit prepared inputs, propagate `--prepared-run` through live/recorded callers, and repair touched current construction fields; update config/usage guidance and tests to verify all three tools, wrong-tool rejection, run-local copies, offline credential-free validation, and no imports of utility/test modules from production code.
- [x] 5.3 Migrate Claude vendor-login and Kimi hook-observation manual smokes to explicit external credentials/private runs and maintained lifecycle commands; update their usage docs and controlled tests to verify no automatic personal-home copy into the checkout, original source preservation, and scoped stop/cleanup.
- [x] 5.4 Migrate maintained interactive exploration launchers and usage qualification instructions to the shared resolved configuration; verify their preparation tests/examples no longer require change-local Qwen wrappers and historical captured model/version facts remain unchanged.
- [x] 5.5 Retire tracked account-specific auth placeholders/guidance after adding protective ignore coverage, and update `tests/fixtures/README.md`, plain-fixture guidance, and `AGENTS.md`; verify a synthetic old local credential stays ignored and no implementation step deletes, moves, or stages operator-owned credentials.
- [x] 5.6 Update getting-started, vendor-login, internals, maintained single-agent/writer-team demo, workflow, and AG-UI Kimi live-validation guidance; verify targeted doc/consumer tests and a maintained-surface audit find no active dependency on old fixture auth roots, personal bundle defaults, or the fixed Yunwu setup.

## 6. Cross-Component Qualification

- [x] 6.1 Run the complete hermetic client/case/mode preparation matrix and consumer integration suites; verify actual generated configurations, effective child env, credential copies, concurrent isolation, public managed identities, and no personal auth/cloud dependency in default automated tests.
- [x] 6.2 Run fresh isolated DeepSeek raw captures and all six managed Claude/Codex/Kimi headless/unattended-TUI lanes with explicit model selection; verify fresh/resumed headless prompts, direct TUI interaction, selected protocol/routing, available public usage evidence, and sanitized exact-version/model reports, then stop run-owned agents.
- [x] 6.3 Qualify configured self-hosted client/mode lanes using an explicit model other than Qwen3.8; verify available compatible protocols through live runs or deliver a report naming each unavailable prerequisite/unsupported protocol without claiming those lanes passed.
- [x] 6.4 Exercise imported native-login smoke when valid explicitly selected local state is available; otherwise record that optional live lane as not run, while verifying synthetic discovery/import/native preparation tests cover every supported client and source/store files remain unchanged.
- [x] 6.5 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, targeted fixture/consumer integration suites, and strict OpenSpec validation; verify all mandatory checks pass, only synthetic credentials are tracked, and shared reports contain no live secret values.

## Workflow Follow-up

- Review and verify the implementation before normal archival and spec synchronization.
- During synchronization/archive, update the existing Codex capability's provider-specific Purpose text to describe its generic API-compatible contract; do not rewrite historical qualification evidence.
