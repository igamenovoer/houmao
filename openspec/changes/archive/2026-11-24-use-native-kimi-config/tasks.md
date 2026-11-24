# Tasks

## 1. Effective Kimi Config

- [x] 1.1 Resolve setup TOML and the adapter-mapped credential TOML in `validate_brain_inputs()`. Carry the resolved config into `build_brain_home()`. Test setup-only fields, distinct aliases, array replacement, and complete replacement of colliding provider, model, and service entries.
- [x] 1.2 Materialize the resolved config as an owner-private runtime file before runtime-owned settings are applied. Verify source bundles remain intact and skills and observation hooks still project. Test that an invalid TOML file or catalog fails before a forced launch takes over a running agent and omits any synthetic secret from diagnostics.
- [x] 1.3 Document config precedence in the build and run references. Verify the documented credential-only alias example resolves without a matching setup entry and preserves setup-only preferences.

## 2. Native Model and Reasoning Selection

- [x] 2.1 Use the effective config's native default and alias catalog during managed launch validation. Verify CLI model selection for headless and TUI, exact TUI continuation, and runtime `default_model` for Web and ACP. Replace tests that expect env-model selection with native config cases.
- [x] 2.2 Map numeric levels in `model_mapping_policy.py` using the effective alias's ordered `support_efforts` after native overrides. Test two catalogs with custom labels, exact label preservation, saturation and provenance, native off capability, omitted levels, and absent or malformed lists.
- [x] 2.3 Apply the same mapping during headless request-scoped overrides using the committed runtime config. Test a different alias for one prompt, successful restoration, and invalid selection without leaving a partial config change. Document how alias selection, one-based indices, off, and saturation work in launch and prompt guidance.

## 3. Environment and Credentials

- [x] 3.1 Add a shared Kimi mapping for supported native TOML destinations and narrow the starter and maintained adapter allowlists. Cover the model, provider, thinking, telemetry, and documented runtime preference families in the design. Test credential validation, specialist/profile env records, one-shot overrides, and older project adapters with retired names. Verify errors name the native field and omit values.
- [x] 3.2 Integrate config-owned name removal with shared launch and relaunch environment preparation. Use isolated tmux coverage with ambient and server-global stale values. Verify the variables are absent in native processes and ordinary panes across fresh launch and relaunch, while the server-global environment and peer sessions retain their own values.
- [x] 3.3 Reuse private launch inputs for API-key references and the retained sampling variables. Test inline config credentials, `api_key_env` with a selected key, a missing key reference, and explicit OAuth import. Verify synthetic secrets are absent from public manifests, pane commands, tmux, and error output.
- [x] 3.4 Update Kimi credential add/set, specialist credential authoring, launch-policy descriptions, and packaged credential guidance. Retire Kimi env-writing flags for supported TOML settings and retain the native imports and optional private API key. Exercise the documented example and verify CLI help and credential inspection match the new contract.

## 4. Fixtures and Maintained Callers

- [x] 4.1 Have `scripts/agents/test-fixtures/fixturelib` write native Kimi config for both API cases and accept ordered model effort metadata. Test raw and manager preparation with the same endpoint, protocol, and explicit model. Check the generated TOML, isolated auth files, and absence of retired launch variables.
- [x] 4.2 Update maintained Kimi demos, tracked fixture assets, and active examples that prepare or import env-model credentials. Run their affected preparation and command tests and confirm the current references explain how to replace a legacy bundle with a native config.

## 5. Integration Verification

- [x] 5.1 Run the maintained self-hosted Kimi Web fixture with an explicitly selected compatible model and a catalog present only in credential TOML. Verify the native model catalog and selected effort, inspect actual isolated tmux and pane environments, submit one managed prompt, and verify exact relaunch and stop.
- [x] 5.2 Run focused launch and model-mapping tests for headless, TUI, ACP, and Web with Pixi. Record the tested Kimi builds, selected cases, and results. Run `pixi run test`, `pixi run lint`, and `pixi run typecheck` to catch regressions in shared launch logic.
