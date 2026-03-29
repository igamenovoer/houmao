## Why

Houmao's active local project model is now a catalog-backed `.houmao/` overlay: `.houmao/houmao-config.toml` is the discovery anchor, `.houmao/catalog.sqlite` plus `.houmao/content/` are the canonical project-local store, and `.houmao/agents/` is a compatibility projection materialized only when file-tree consumers still need `roles/`, `tools/`, and `skills/` on disk.

The remaining drift is that active resolver code, deprecated compatibility entrypoints, help text, tests, and maintained demo helpers still preserve `.agentsys` as the ambient no-config fallback or generated path family. Active docs also still describe `.agentsys` as if it were a supported current fallback even though local workflows have moved to `.houmao/`.

## What Changes

- **BREAKING** retire `.agentsys/agents` as the ambient no-config fallback for active local build and pair-native launch flows that consume a filesystem agent-definition tree.
- Keep discovered `.houmao/houmao-config.toml` as the project-discovery anchor for those flows; when a project overlay is discovered, pair-native build and launch paths continue to materialize the compatibility projection from the catalog-backed `.houmao/` overlay before reading presets, role prompts, or tool assets.
- Change the no-config default agent-definition root for filesystem consumers from `<cwd>/.agentsys/agents` to `<cwd>/.houmao/agents`.
- Update `houmao-mgr project init` compatibility validation/bootstrap so it respects an existing configured `paths.agent_def_dir` value for the compatibility projection instead of treating only `.houmao/agents` as compatible.
- Move remaining maintained `.agentsys*` generated or scratch defaults for demo-owned agent trees and headless scratch outputs to `.houmao/*` or other Houmao-owned path families, and refresh the corresponding docs, help text, and tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-cli`: repo-local discovery and init SHALL stop preserving legacy `.agentsys` fallback behavior while keeping the catalog-backed `.houmao` overlay as the canonical project model and `.houmao/agents/` as a compatibility projection.
- `brain-launch-runtime`: deprecated standalone build/start compatibility entrypoints SHALL stop falling back to `.agentsys` when they resolve filesystem agent-definition inputs.
- `docs-getting-started`: getting-started guidance SHALL describe the catalog-backed `.houmao` overlay and `.houmao`-only ambient fallback rather than presenting `.agentsys` as a supported current path.
- `docs-cli-reference`: CLI reference docs that still mention deprecated compatibility entrypoints or resolution precedence SHALL not present `.agentsys` as a supported default or fallback path.
- `houmao-owned-dir-layout`: maintained workspace-local defaults and generated scratch paths that still derive from `.agentsys*` SHALL move to `.houmao` or other Houmao-owned path families.

## Impact

- Affected code: `src/houmao/project/overlay.py`, `src/houmao/agents/native_launch_resolver.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/agents/realm_controller/cli.py`, `src/houmao/agents/realm_controller/backends/headless_runner.py`, maintained demo helpers under `src/houmao/demo/shared_tui_tracking_demo_pack/`, and supported demo scripts/docs under `scripts/demo/`.
- Affected docs: getting-started docs, CLI reference docs, README/current contributor guidance that still describe live `.agentsys` fallback behavior, and maintained demo/tutorial docs.
- Affected tests: project overlay resolution tests, shared native-launch resolution tests, standalone CLI resolution tests, and maintained demo path assertions.
