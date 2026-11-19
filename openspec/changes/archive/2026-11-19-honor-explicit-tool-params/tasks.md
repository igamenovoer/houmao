# Tasks

## 1. Field Precedence and Validation

- [x] 1.1 Resolve supported native setup and argument aliases alongside the existing typed layers, preserving presence and precedence before materialization. Extend `test_tool_params.py` to verify inherited fields, one-shot overrides, and supported explicit false, empty, or null values.
- [x] 1.2 Validate reserved fields and equivalent managed launch overrides before merge and takeover. Test matching and null values, a shadowed lower-layer request, unsupported backend combinations, and an invalid force launch that leaves its predecessor intact.
- [x] 1.3 Use the version-selected launch policy to fill permission omissions and record the resolved values and sources. Extend launch-policy and runtime tests for shared helper and managed startup, reused homes, `as_is`, exact relaunch, and preservation of unrelated setup and credential data.
- [x] 1.4 Document field precedence and reserved-setting diagnostics in the launch-policy and launch-overrides references. Check the inherited and one-shot examples against the corresponding parameter-resolution tests.

## 2. DSH Defaults and Self Status

- [x] 2.1 Expose DSH sandbox and approval fields and reserve the managed `hmr` setting. Remove authored `hmr` from starter setups, fixtures, and examples. Verify field-level merging, rejection of authored `hmr: false`, and successful loading of the updated starter setups.
- [x] 2.2 Project the resolved DSH sandbox, approval, and matching preset from one input in headless, ACP service, and Web startup. Extend DSH configuration and launch tests for omitted fields, each independent override, `as_is`, repeated launch, and a Web session that uses explicit interactive approval.
- [x] 2.3 Route `agents self state` and `agents self mail status` through read-only current-session resolution. Exercise signed gateway status and detached local status, verify rejection of stale or invalid authority, and assert the lookup performs no registry lock acquisition or gateway publication. Update the lifecycle reference with current-session status behavior.
- [x] 2.4 Qualify the three DSH profiles on the supported reference build. Use `scripts/agents/test-fixtures/fixture.py` with the `self-hosted` case, `Qwen/Qwen3.8-27B-FP8`, and an isolated run root. Verify a harmless sibling-path write succeeds with the default and is refused with explicit `workspace-write`. Verify both self-status commands succeed inside the restricted headless agent and record the policy and outcomes.
- [x] 2.5 Document the DSH permission fields, the previous workspace-restricted posture as an explicit configuration, and `hmr` migration. Verify the example settings load and match the profile exercised in qualification.

## 3. Claude, Codex, and Kimi Startup

- [x] 3.1 Apply Claude's resolved permission mode to the private home and native startup. Extend launcher tests for omitted unattended permissions, a supported authored restricted mode, `as_is`, and startup warning handling, and check the resulting command and config agree.
- [x] 3.2 Apply resolved Codex approval and sandbox to the runtime home and final CLI options. Extend launch-policy tests to verify copied setup values, explicit native flags, typed overrides, and project-local config precedence without discarding provider or model settings.
- [x] 3.3 Use the same resolved Codex policy at app-server thread start and resume. Verify the request and echoed effective policy for defaults and an explicit override, and cover a mismatch that prevents readiness.
- [x] 3.4 Apply resolved Kimi TUI permission on fresh and exact-resume startup. Verify the omitted auto default, a supported explicit override, a native prompt-mode incompatibility before headless start, and preservation of the role projection and exact session selectors.
- [x] 3.5 Apply the resolved Kimi policy through qualified ACP and Web session startup or binding surfaces. Verify a supported authored value and the omitted auto default on initial launch and exact continuation. Exercise preservation of live session settings during observation and gateway reattachment.
- [x] 3.6 Document provider-specific fields and mode or continuation limits in the launch-policy, backend, and lifecycle references. Confirm the examples agree with the provider launch tests and pass the strict docs build.

## 4. Integration Verification

- [x] 4.1 Run `pixi run lint`, `pixi run typecheck`, `pixi run test`, and the affected provider and CLI integration suites with isolated tmux and test roots. Record commands and results, including the manager, authenticated gateway, and relevant relaunch paths.
- [x] 4.2 Run `openspec validate honor-explicit-tool-params --strict` and review the implemented CLI and native settings against each changed requirement. Confirm each provider and both DSH self-status regressions have corresponding verification evidence.
