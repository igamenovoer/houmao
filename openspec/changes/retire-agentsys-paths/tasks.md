## 1. Resolver And Project Bootstrap

- [x] 1.1 Change the shared project-aware agent-definition resolver to use `<cwd>/.houmao/agents` as the no-config default instead of `.agentsys/agents`.
- [x] 1.2 Update `houmao-mgr project init` to read an existing `.houmao/houmao-config.toml`, resolve `paths.agent_def_dir`, and use that configured compatibility-projection root for validation and optional compatibility-profile bootstrap without materializing optional projection trees on plain init.
- [x] 1.3 Refresh project-overlay tests to cover the new `.houmao` fallback and re-run-init behavior for custom configured compatibility-projection roots.

## 2. Pair-Native, Compatibility, And Maintained Path Defaults

- [x] 2.1 Update pair-native local build/launch resolution paths and tests to retire `.agentsys` fallback, including `houmao-mgr brains build`, `houmao-mgr agents launch`, and shared native launch resolution.
- [x] 2.2 Update deprecated standalone `build-brain` and `start-session` compatibility entrypoints and help text to match the `.houmao` fallback contract while keeping those surfaces explicitly legacy.
- [x] 2.3 Move active maintained `.agentsys*` generated or scratch defaults to `.houmao` or other Houmao-owned paths, including shared demo-generated agent trees and headless fallback scratch roots, and refresh the matching tests.

## 3. Docs And Verification

- [x] 3.1 Update active getting-started docs, CLI reference docs, README/current contributor guidance, and maintained demo/tutorial docs to document the catalog-backed `.houmao` overlay plus `.houmao` ambient fallback and to remove `.agentsys` as a supported default or fallback path.
- [x] 3.2 Clean up active supporting metadata such as help text and maintained demo/tutorial references so current or deprecated guidance no longer preserves `.agentsys` fallback behavior.
- [x] 3.3 Verify the change with focused searches and relevant test runs, leaving clearly archival/legacy `.agentsys` references and `AGENTSYS_*` env names untouched.
