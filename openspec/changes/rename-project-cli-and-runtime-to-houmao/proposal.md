## Why

The repository currently presents three competing public identities: the project is branded as `gig-agents`, the main operator CLI is `gig-agents-cli`, and the runtime surface is documented and referenced as `brain_launch_runtime`. The naming rationale under `context/design/namings/` has already converged on `Houmao` for the project and `realm_controller` for the runtime, but the repo still exposes the older names across packaging, docs, context notes, scripts, tests, and OpenSpec artifacts.

This should be corrected now while the system is still under active development and before more docs, specs, and helper workflows harden around the old names. A narrow, explicit rename also prevents accidental drift into broader lore-driven renames that would change subcommands, class/function names, protocol env vars, or unrelated package paths.

## What Changes

- **BREAKING** Rename the project/distribution-facing identity from `gig-agents` to `Houmao` across packaging metadata, README/docs, active guidance, and selected historical text updates outside `context/logs/`.
- **BREAKING** Rename the primary console script from `gig-agents-cli` to `houmao-cli` while keeping the existing runtime subcommands unchanged.
- **BREAKING** Rename the runtime module surface from `gig_agents.agents.brain_launch_runtime` to `gig_agents.agents.realm_controller`, including direct module invocation examples, internal imports, tests, doc page names, and related spec references.
- Preserve the existing Python package root `gig_agents`, the CAO launcher CLI `gig-cao-server`, current runtime subcommands, and current class/function naming except where the module rename requires import-path updates.
- Revise the naming rationale docs under `context/design/namings/` so they reflect the chosen narrow rename scope rather than the broader alternative renames explored earlier.
- Update OpenSpec specs and change artifacts that currently name the old project, CLI, or runtime surface so the documented contract matches the intended public naming.

## Capabilities

### New Capabilities
- `project-cli-identity`: Defines the repository-facing project name as `Houmao`, the primary operator CLI as `houmao-cli`, and the explicit non-goals for package-root, CAO launcher, subcommand, and protocol naming.

### Modified Capabilities
- `brain-launch-runtime`: Rename the public runtime module/documentation surface to `realm_controller` without changing the existing runtime behavior or subcommand set.
- `brain-launch-runtime-pydantic-boundaries`: Update the documented packaged schema discovery path to the renamed runtime module tree.
- `cao-interactive-demo-operator-workflow`: Rename demo workflow references that currently instruct operators to use `brain_launch_runtime` commands.
- `cao-interactive-full-pipeline-demo`: Rename the interactive full-pipeline demo's shared runtime invocation references from `brain_launch_runtime` to `realm_controller`.

## Impact

- Affected packaging and repo metadata: `pyproject.toml`, `README.md`, docs indexes, contributor instructions, and branding/notice text.
- Affected runtime code and tests: `src/gig_agents/agents/brain_launch_runtime/**`, direct importers such as `src/gig_agents/cli.py`, and runtime test trees under `tests/unit/agents/` and `tests/integration/agents/`.
- Affected docs and helper scripts: runtime reference pages, mailbox/gateway/agent docs that link to runtime paths, demo scripts, migration notes, and parity helpers.
- Affected repository knowledge and specs: `context/` content excluding `context/logs/`, active OpenSpec specs, and archived OpenSpec text or path references that still describe the old names.
