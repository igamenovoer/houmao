# Implementation Verification

## Repository Checks

- `pixi run lint` passed.
- `pixi run typecheck` passed across 522 source files.
- `pixi run test` passed 5,001 unit tests with 14 skipped. The suite used six workers and isolated tmux and pytest roots. Passing `--basetemp` as a task argument kept nested pytest fixture tests from inheriting the outer temporary-root option.
- `pixi run docs-build` passed with strict MkDocs validation.
- `openspec validate honor-explicit-tool-params --strict` passed.
- The focused launcher, field resolution, version and force preflight, and manager command suite passed 296 cases. The generated helper also ran against a fixture executable and preserved an explicit typed permission value and trailing manual arguments.
- The gateway runtime and focused HTTPS self-status integration run passed 14 cases. Both publication-denied cases used current-session authority. Attached mail status used a signed gateway request, and detached mail status used the local mailbox binding.
- The DSH relaunch, resumed control, service gateway, and headless admission integration suite passed all nine cases with DSH `0.2.2-rc.3`. The initially selected PATH executable reported `0.2.2-rc.1` and failed the supported-version check. The rerun used the qualified repository-local runtime.

```bash
env -u TMUX -u TMUX_PANE -u PYTEST_ADDOPTS TMUX_TMPDIR="$isolated_tmux_dir" \
  PYTHON_CPU_COUNT=12 pixi run test --basetemp="$test_root"

env -u TMUX -u TMUX_PANE TMUX_TMPDIR="$isolated_tmux_dir" \
  HOUMAO_DSH_EXECUTABLE="$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" \
  pixi run pytest -q --basetemp="$test_root" \
  tests/integration/agents/dsh/test_refresh_relaunch.py \
  tests/integration/agents/dsh/test_resumed_control.py \
  tests/integration/agents/dsh/test_service_gateway.py \
  tests/integration/agents/dsh/test_headless_dispatch_permission.py
```

## Requirement Review

| Capability | Evidence |
| --- | --- |
| `recipe-launch-overrides` | Field resolution tests cover native setup values, typed and raw precedence, explicit false and null, and a lower-layer reservation. Force tests verify invalid protocol settings, unsupported backend combinations, and an incompatible executable leave the predecessor intact. |
| `versioned-launch-policy-registry` | Provider strategies declare omitted-field defaults. Policy tests cover startup diagnostics, config and final CLI agreement, a reused home restored to its native baseline under `as_is`, and an actual generated helper invocation. |
| `brain-launch-runtime` | The [Claude and Codex checks](claude-codex-qualification.md) cover private-home projection, final CLI overrides, app-server policy echo, and exact continuation. The [DSH qualification](dsh-qualification.md) covers coherent native presets across headless, ACP, and Web, including browser approval and continued sessions. |
| `kimi-code-tui-support` | [Kimi qualification](kimi-permissions.md) covers default and explicit permission modes, native TUI continuation, headless compatibility, ACP and Web startup and continuation, and preservation of live Web settings during reads and gateway reattachment. |
| `houmao-mgr-project-easy-cli` | Live manager fixtures qualified specialist-backed launch with omitted fields and authored overrides. The fixture and project command suites exercise the same delegation path. |
| `houmao-srv-ctrl-native-cli` | The live restricted DSH agent ran both self-status commands. Manager tests reject stale tmux identity. The attached and detached integration cases disallow registry locking and capability publication while exercising the signed gateway and local status routes. |
| `docs-launch-policy-reference` and `docs-run-phase-reference` | The strict build checks the revised precedence, DSH migration, provider field tables, Kimi mode limits, and lifecycle documentation. |

The [HTTPS integration log](gateway-https.md) records the isolated pass and an existing public handoff race reproduced with identical synchronization on archived baseline code. The [Claude and Codex qualification log](claude-codex-qualification.md) also records a separate older Codex TUI proxy fixture whose synthetic version falls below native support.
