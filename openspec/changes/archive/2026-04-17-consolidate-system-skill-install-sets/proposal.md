## Why

Recent system-skill work added a workspace-management utility and then changed the packaged catalog to avoid unsafe partial installs, but the OpenSpec specs still describe the older granular set model. The specs need to catch up so the implemented behavior has a clear contract and future catalog edits preserve internal skill-routing closure.

## What Changes

- Add a new packaged utility capability for `houmao-utils-workspace-mgr`, covering plan/execute workspace preparation before agents are launched.
- **BREAKING**: Replace the old granular installable set surface (`mailbox-*`, `agent-memory`, `user-control`, `agent-*`, `utils`, and similar set names) with two installable sets:
  - `core`: closed automation plus operator-control system-skill surface, excluding utility workflows.
  - `all`: `core` plus utility workflows.
- Change fixed auto-install defaults:
  - managed launch uses `core`,
  - managed join uses `core`,
  - CLI default uses `all`.
- Require packaged installable sets to be closed over internal system-skill routing so a skill installed through a set does not route to another catalog skill omitted from the same set.
- Update user-facing documentation requirements for README, the system-skills CLI reference, the system-skills overview guide, and managed-memory docs to describe `automation`, `control`, and `utils` as organization groups while keeping only `core` and `all` as installable set names.

## Capabilities

### New Capabilities

- `houmao-utils-workspace-mgr-skill`: Packaged utility system skill for planning and executing multi-agent workspace layouts, including in-repo and out-of-repo workspaces, Git worktrees, local-only shared repos, submodule materialization policy, launch-profile cwd updates, and optional memo-seed workspace rules.

### Modified Capabilities

- `houmao-system-skill-installation`: Replace granular named-set requirements with closed `core` and `all` installable sets, update fixed auto-install defaults, and require set closure over internal skill-routing references.
- `houmao-system-skill-families`: Replace the explicit-only `utils` set model with conceptual `automation`, `control`, and `utils` organization groups plus installable `core` and `all` sets.
- `houmao-mgr-system-skills-cli`: Update `system-skills list` and `install` requirements so the CLI reports and accepts `core`/`all`, uses `all` for omitted CLI selection, and no longer documents old granular set names as current.
- `docs-system-skills-overview-guide`: Update the overview guide requirements to include `houmao-utils-workspace-mgr`, organize skills under automation/control/utils, and describe managed `core` versus CLI-default `all`.
- `docs-readme-system-skills`: Update README requirements so the system-skills table includes `houmao-utils-workspace-mgr` and the auto-install paragraph describes `core` and `all`.

## Impact

- Affected catalog/runtime code: `src/houmao/agents/assets/system_skills/catalog.toml`, `src/houmao/agents/system_skills.py`.
- Affected packaged skill assets: new `src/houmao/agents/assets/system_skills/houmao-utils-workspace-mgr/`; install wording in `houmao-utils-llm-wiki`.
- Affected docs: `README.md`, `docs/getting-started/system-skills-overview.md`, `docs/reference/cli/system-skills.md`, and `docs/getting-started/managed-memory-dirs.md`.
- Affected tests: system-skill catalog/installer tests, CLI command tests, and docs guard tests.
