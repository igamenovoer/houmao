# Pending-Input Implementation Validation

## Result

The pending-input tracking and gateway admission-policy change passes its focused deterministic suites, runtime suite, recorded replay qualification, live admission qualification, formatting, lint, whitespace, and strict OpenSpec validation. The full unit run has no change-related failure. Existing repository and environment failures are listed separately below.

## Focused Deterministic Suites

All focused commands ran through Pixi after formatting:

| Scope | Command | Result |
|---|---|---:|
| Shared TUI tracking and provider profiles | `pixi run pytest tests/unit/shared_tui_tracking -q` | 121 passed |
| Terminal recording, labels, replay, and cadence | `pixi run pytest tests/unit/terminal_record/test_service.py -q` | 24 passed |
| Gateway models, service, policies, and fake-adapter race | `pixi run pytest tests/unit/agents/realm_controller/test_gateway_support.py -q` | 117 passed |
| Passive-server observation and proxy | `pixi run pytest tests/unit/passive_server/test_app_contracts.py tests/unit/passive_server/test_service.py -q` | 154 passed |
| Server models, clients, and TUI projection | `pixi run pytest tests/unit/server/test_app_contracts.py tests/unit/server/test_client.py tests/unit/server/test_tui_parser_and_tracking.py -q` | 72 passed |
| Maintained CLI and packaged system skills | `pixi run pytest tests/unit/srv_ctrl/test_commands.py tests/unit/srv_ctrl/test_managed_agents.py tests/unit/agents/test_system_skills.py -q` | 189 passed |

The first full unit run exposed one omitted `surface_pending_input` constructor argument in an exploratory comparison test. The test was updated and passed in isolation. The post-fix full run reported 2,396 passed, 13 skipped, and the two unrelated failures below.

`pixi run test-runtime` passed all 856 runtime-focused tests.

## Recorded and Live Qualification

The recorded UC-05 qualification report is `20260714T191157Z-uc05-pending-input-replay-qualification.md`. Its audited Claude, Codex, and Kimi canonical streams contain 3,634 samples with zero pending-input mismatches. All 18 deterministic cadence variants also have zero mismatches and no cadence-only oscillation.

The unattended live UC-06 report is `20260714T194201Z-uc06-live-admission-qualification.md`. Claude, Codex, and Kimi passed the real CLI/gateway admission-policy sequence. Codex inherited the configured proxy environment, including the current port 7990 setting. Its upstream model request still timed out after fallback, so the report marks provider completion as externally tainted while retaining the passing gateway-policy evidence. No Gemini process was launched.

## Static and Specification Checks

- `pixi run format` completed and reformatted eight touched Python files.
- `pixi run lint` passed.
- `git diff --check` passed.
- `openspec validate track-tui-pending-instructions --strict` passed.
- The maintained gateway source, CLI, docs, and packaged skills contain no direct prompt-control `force` or `forced` compatibility path. Remaining matches are strict rejection assertions, an unrelated mailbox registration mode, or ordinary prose about unrelated behavior.

`pixi run typecheck` reports seven pre-existing errors outside the pending-input and admission-policy paths:

- one return-value error in `src/houmao/agents/managed_launch_force.py`
- two return-value errors in `src/houmao/agents/managed_prompt_header.py`
- four literal-type errors in `src/houmao/agents/launch_policy/engine.py`

No type error points to a file or interface changed for pending-input tracking.

## Unrelated Baseline Failures

The post-fix `pixi run test` failures are:

1. `tests/unit/ag_ui/test_plotly_trace_catalog.py::test_plotly_trace_catalog_generated_artifacts_are_current` cannot find the local reference file `extern/orphan/plotly.js/dist/plot-schema.json`.
2. `tests/unit/srv_ctrl/commands/test_ag_ui_authoring.py::test_gateway_ag_ui_publish_does_not_accept_third_party_endpoint_option` expects an older Click error spelling (`No such option '--endpoint'`) while the installed Click emits `No such option: --endpoint`.

Neither test file was changed by this work.

The standalone `tests/integration/srv_ctrl/test_cli_shape_contract.py` run reported 5 passed and 17 failed. Sixteen failures still invoke removed top-level `agents launch`, `agents join`, or `agents mail` commands. The remaining failure expects an obsolete project-overlay status value. This change only adds required pending fields to two fake tracked-state constructors in that file; it does not restore retired command surfaces.

## Conclusion

The implemented change meets the pending-input detector, propagation, replay, admission-policy, CLI, proxy, documentation, system-skill, recorded-data, and live-provider requirements. The outstanding failures are isolated from the changed behavior and are recorded here rather than treated as qualification failures.
