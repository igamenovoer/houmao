## 1. Launch-Policy Contract

- [x] 1.1 Update launch-policy registry metadata and validation so unattended compatibility is defined by strategy-owned config/state and launch surfaces for all supported tools, not by auth material alone.
- [x] 1.2 Extend unattended launch processing to canonicalize tool-specific launch overrides that target strategy-owned no-prompt surfaces, including config-override syntax where applicable.
- [x] 1.3 Align existing tool-specific bootstrap/runtime-home mutation helpers with the shared launch-policy contract so unattended-owned state is force-overridden on the runtime copy.

## 2. Runtime Construction

- [x] 2.1 Ensure brain/runtime construction copies the selected setup bundle into the runtime home before unattended launch-policy mutation runs.
- [x] 2.2 Preserve non-owned setup content while overwriting strategy-owned unattended state in the runtime home for the selected tool.
- [x] 2.3 Update runtime error reporting so credential-readiness failures remain distinct from unattended-strategy compatibility failures.

## 3. Project-Easy Setup Persistence

- [x] 3.1 Add explicit `--setup` support to `houmao-mgr project easy specialist create` with tool-scoped setup validation.
- [x] 3.2 Persist the selected setup consistently into project catalog metadata and generated specialist presets instead of hardcoding `default`.
- [x] 3.3 Ensure project-easy instance launch continues to use the stored specialist setup without inferring setup from credentials.

## 4. Verification

- [x] 4.1 Add or update unit tests for unattended runtime-home override ordering and conflicting launch-input canonicalization across current unattended tools, including Claude and Codex.
- [x] 4.2 Add or update project-easy CLI tests covering explicit non-default setup persistence and default setup persistence across supported tools.
- [x] 4.3 Re-run unattended launch validation for current TUI/headless tools and record the results against the corrected authoritative unattended contract.

## Verification Notes

- 2026-03-30: `pixi run pytest tests/unit/agents/test_launch_policy.py tests/unit/agents/realm_controller/test_codex_bootstrap.py tests/unit/agents/test_brain_builder.py::test_build_brain_home_copies_selected_setup_bundle_verbatim tests/unit/srv_ctrl/test_project_commands.py::test_project_easy_specialist_create_persists_non_default_setup tests/unit/srv_ctrl/test_project_commands.py::test_project_easy_specialist_create_persists_default_setup_for_supported_tools tests/unit/srv_ctrl/test_project_commands.py::test_project_easy_instance_launch_uses_stored_specialist_setup` passed (`29 passed`).
- 2026-03-30: `pixi run ruff check src/houmao/agents/launch_policy/provider_hooks.py src/houmao/agents/launch_policy/engine.py src/houmao/agents/realm_controller/backends/codex_bootstrap.py src/houmao/srv_ctrl/commands/project.py tests/unit/agents/test_launch_policy.py tests/unit/agents/realm_controller/test_codex_bootstrap.py tests/unit/agents/test_brain_builder.py tests/unit/srv_ctrl/test_project_commands.py` passed.
- 2026-03-30: `pixi run mypy src/houmao/agents/launch_policy/provider_hooks.py src/houmao/agents/launch_policy/engine.py src/houmao/agents/realm_controller/backends/codex_bootstrap.py src/houmao/srv_ctrl/commands/project.py` still reports the pre-existing unrelated error in `src/houmao/agents/realm_controller/backends/tmux_runtime.py:374`.
