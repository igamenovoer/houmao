## Why

The repository has already been rebranded in code and on GitHub, but several active-facing surfaces still teach the old `gig-agents` name, old `gig-agents-cli` entrypoint, old `brain_launch_runtime` path, old `gig_agents` Python package root, or old GitHub slug. The package metadata now says `Houmao`, but the source tree and module-entrypoint examples still use `src/gig_agents` and `python -m gig_agents...`, which leaves the public identity split across two namespaces.

This should be cleaned up now before more edits, automation, generated guidance, and runtime helper outputs keep reintroducing the superseded names. User-facing surfaces should not leak the historical project or module name at all: after this rename, readers of shipped source, docstrings, CLI help, and documentation should only encounter the Houmao identity.

At the same time, the repo needs an explicit policy boundary so maintainers know which old references are restricted to non-user-facing archive/provenance material and which ones must be updated to the canonical Houmao identity.

## What Changes

- Define a canonical repository-identity policy for active-facing metadata, contributor guidance, AI-assistant instruction files, and Python package/module surfaces after the GitHub slug rename to `houmao`.
- Rename the canonical Python package root from `src/gig_agents` to `src/houmao`, and update internal imports, module-entrypoint examples, build metadata, package-resource lookups, generated helper imports, and repo-owned scripts/tests/docs to use `houmao...`.
- Rename remaining user-facing CLI surfaces so the launcher is published as `houmao-cao-server` instead of `gig-cao-server`.
- Update high-value active surfaces such as package metadata URLs, assistant instruction docs, contributor guidance, shipped docstrings, and repo-owned documentation so they use `Houmao`, `houmao-cli`, `houmao-cao-server`, `houmao.agents.realm_controller`, and the current GitHub repository URL.
- Define and apply a path-reference policy for active instructional docs: execution-oriented guidance should avoid hardcoded host-specific checkout paths when placeholders or relative paths are sufficient.
- Preserve explicit historical, provenance, archive, and observed-path references only in non-user-facing materials whose purpose is to document what happened rather than instruct the reader what to do now.

## Capabilities

### New Capabilities
- `repo-identity-guidance`: Defines the canonical project/repository identity, Python package namespace, and path-reference policy for active-facing metadata, contributor docs, assistant instructions, and instructional guidance.

### Modified Capabilities
- `brain-launch-runtime`: Move runtime package-path and packaged-schema references to the canonical `houmao` package tree.
- `brain-launch-runtime-pydantic-boundaries`: Move packaged schema discovery references to `houmao/agents/realm_controller/schemas/`.
- `cao-server-launcher`: Rename the canonical launcher CLI surface to `houmao-cao-server` and align user-facing launcher references with the Houmao namespace.
- `cao-server-launcher-demo-pack`: Make the canonical launcher tutorial/demo invoke `houmao.cao.tools.cao_server_launcher`.
- `cao-interactive-demo-module-structure`: Make the canonical demo package path `houmao.demo.cao_interactive_demo` under `src/houmao/demo/`.
- `cao-interactive-demo-operator-workflow`: Clarify that active tutorial and operator guidance should use canonical `houmao` module paths, canonical Houmao CLI names, and avoid teaching host-specific checkout paths as executable defaults when relative or placeholder paths are sufficient.

## Impact

- Affected source/package surfaces: `src/gig_agents/**` to `src/houmao/**`, `pyproject.toml` entry points/build package lists, packaged resource lookups, generated bootstrap snippets, and subprocess/module-launch strings
- Affected metadata and repo settings docs: `pyproject.toml`, contributor-facing docs, assistant instruction files such as `CLAUDE.md` and `.github/copilot-instructions.md`, and shipped documentation under `README.md` and `docs/`
- Affected repo-owned tests and scripts: monkeypatch/import targets, demo wrappers, launcher demos, helper scripts, and module-invocation examples that currently use `gig_agents...`
- Affected user-facing runtime strings: module docstrings, CLI help/output references, and published launcher/runtime binary names
- Affected path-policy guidance: `AGENTS.md`, selected docs under `docs/`, and selected active `context/` notes outside `context/logs/`
- Affected migration expectations: previously generated runtime homes that embed `gig_agents` bootstrap imports may need rebuild after the package rename
- Affected OpenSpec docs: new policy capability spec plus deltas for capabilities that currently define `gig_agents` package paths or `gig-*` CLI surfaces as canonical
