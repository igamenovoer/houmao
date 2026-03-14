## 1. CAO Boundary Compatibility

- [x] 1.1 Update `src/houmao/cao/models.py`, `src/houmao/cao/__init__.py`, and `tests/unit/agents/realm_controller/test_cao_client_and_profile.py` so terminal `provider` parses as a forward-compatible non-empty string, `CaoProvider` is no longer the public response-model export, and terminal `status` remains a validated enum.
- [x] 1.2 Keep `_CAO_PROVIDER_BY_TOOL` explicit in `src/houmao/agents/realm_controller/backends/cao_rest.py`, and add negative coverage that parsed upstream provider ids (for example `kimi_cli`) do not automatically widen runtime launch support.
- [x] 1.3 Introduce one explicit shared shadow-parser-support helper/set used by `src/houmao/agents/realm_controller/launch_plan.py` and `src/houmao/agents/realm_controller/backends/cao_rest.py`, with tests covering explicit `cao_only` and rejected `shadow_only` for tools without that capability.

## 2. Runtime and Operator Guidance Cleanup

- [x] 2.1 Update `docs/reference/cao_server_launcher.md`, `docs/reference/cao_shadow_parser_troubleshooting.md`, and the launcher capability delta spec so `home_dir` is described as the CAO state/profile-store anchor rather than a repo-owned workdir-containment rule.
- [x] 2.2 Refresh the remaining demo/help wording that still implies containment semantics, starting with `src/houmao/demo/cao_interactive_demo/cli.py` and `scripts/demo/cao-interactive-full-pipeline-demo/README.md`, so `<launcher-home>/wktree` is described as a demo-owned isolation default rather than a CAO requirement.
- [x] 2.3 Refresh any affected unit tests, fixtures, or golden text that currently assert the old provider enum surface or stale workdir guidance, with primary attention to `tests/unit/agents/realm_controller/test_cao_client_and_profile.py`, `tests/unit/demo/test_cao_interactive_demo.py`, and `tests/integration/demo/test_cao_interactive_demo_cli.py`.

## 3. Verification

- [x] 3.1 Run the focused CAO/runtime/demo test suites that cover boundary parsing, CAO-backed launch validation, launcher behavior, and interactive demo surfaces.
- [x] 3.2 Manually sanity-check the updated docs/examples against the synced upstream CAO behavior so the repo guidance no longer contradicts current upstream behavior.
