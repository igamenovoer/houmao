## 1. Terminology And Path Foundations

- [x] 1.1 Add native-agent and launch-dossier terminology helpers/constants for CLI text, config drafts, command templates, and system skills.
- [x] 1.2 Replace maintained `HOUMAO_AGENT_DEF_DIR` usage with `HOUMAO_NATIVE_AGENT_ROOT` for direct native-agent internals, preserving only intentional compatibility diagnostics if selected.
- [x] 1.3 Change the shared Houmao config/root resolver to use `platformdirs.user_config_path(appname="houmao", appauthor=False)` as the default shared anchor.
- [x] 1.4 Update registry, runtime, mailbox, and owned-path tests for the platformdirs-backed registry default and preserved env override behavior.

## 2. Project Requirement And Overlay Resolution

- [x] 2.1 Change ordinary stateful project-aware local commands to require an active project overlay instead of bootstrapping `<cwd>/.houmao`.
- [x] 2.2 Keep `houmao-mgr project init` as the explicit project creation/validation path and keep `project status` read-only.
- [x] 2.3 Update selected-overlay diagnostics to explain missing project state and point to `houmao-mgr project init` or explicit project overlay selection.
- [x] 2.4 Update tests that currently expect auto-bootstrap from create/launch flows to expect missing-project failure or explicit init setup.

## 3. CLI Command Tree Refactor

- [x] 3.1 Promote `project easy specialist` commands to `project specialist` while preserving specialist semantics and catalog/projection behavior.
- [x] 3.2 Promote `project easy profile` commands to `project profile` while preserving profile semantics, skill overlays, memo seeds, managed-header policy, and replacement/patch behavior.
- [x] 3.3 Promote `project easy instance` lifecycle commands to the selected project-scoped managed-agent command group and remove `easy` from public project help.
- [x] 3.4 Move low-level role commands from `project agents roles` to `internals native-agent roles`.
- [x] 3.5 Move low-level recipe/preset commands from `project agents presets|recipes` to `internals native-agent recipes`, with any retained preset naming treated as internal compatibility only.
- [x] 3.6 Move explicit recipe-backed launch-profile commands from `project agents launch-profiles` to `internals native-agent launch-dossiers`.
- [x] 3.7 Move provider tool/setup commands from `project agents tools` to `internals native-agent tools`.
- [x] 3.8 Update root CLI registration, command help text, and CLI shape tests for removed/promoted paths.

## 4. Projection And Data Model Behavior

- [x] 4.1 Ensure project specialist/profile commands still materialize native-agent compatibility projections required by build and launch internals.
- [x] 4.2 Ensure direct `internals native-agent` commands mutate only the selected native-agent root and do not mutate project catalog state.
- [x] 4.3 Rename user-facing structured output fields from easy/raw/launch-profile language to specialist/profile/native-agent/launch-dossier language where ordinary users see them.
- [x] 4.4 Preserve internal catalog lane identifiers only where needed to avoid unnecessary storage churn, and hide retained names behind user-facing renderers.

## 5. Agent-Facing Surfaces And Documentation

- [x] 5.1 Update command-template ids, families, target argv, renderer scenarios, and tests for promoted project commands and native-agent internals.
- [x] 5.2 Update config-draft ids, generated YAML, blockers, and tests for `project.specialist`, `project.profile`, and `internals.native-agent.launch-dossier`.
- [x] 5.3 Update packaged system skills to route ordinary requests to project specialist/profile commands and explicit native requests to `internals native-agent`.
- [x] 5.4 Update README, getting-started docs, CLI references, registry docs, project-manager references, and release notes language for first-class projects and platformdirs registry defaults.
- [x] 5.5 Update OpenSpec main specs impacted by command paths, terminology, and shared-root behavior after implementation is verified.

## 6. Verification

- [x] 6.1 Run focused unit tests for project overlay resolution, owned paths, registry storage, project command shapes, command templates, config drafts, and system skills.
- [x] 6.2 Run `pixi run lint`.
- [x] 6.3 Run `pixi run typecheck`.
- [x] 6.4 Run `pixi run test`.
- [x] 6.5 Run strict OpenSpec validation for the active change and main specs.
