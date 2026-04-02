## MODIFIED Requirements

### Requirement: Agent definition directory layout documented
The getting-started section SHALL include a page documenting the default Houmao project overlay rooted at `.houmao/` beneath the working directory, including:

- `.houmao/houmao-config.toml`
- `.houmao/.gitignore`
- `.houmao/agents/skills/<skill>/`
- `.houmao/agents/roles/<role>/system-prompt.md`
- `.houmao/agents/roles/<role>/presets/<tool>/<setup>.yaml`
- `.houmao/agents/tools/<tool>/adapter.yaml`
- `.houmao/agents/tools/<tool>/setups/<setup>/`
- `.houmao/agents/tools/<tool>/auth/<auth>/`
- optional `.houmao/agents/compatibility-profiles/`
- optional `.houmao/mailbox/`

That page SHALL explain the purpose of each subdirectory and SHALL make clear that the `.houmao/` overlay is local-only by default.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override for selecting the overlay directory directly in CI or controlled automation.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as an ambient discovery-mode env where `ancestor` remains the default and `cwd_only` restricts ambient lookup to `<cwd>/.houmao/houmao-config.toml`.

That page SHALL distinguish:

- `project agents ...` as the low-level filesystem-oriented project source surface,
- `project easy ...` as the higher-level specialist and instance UX,
- `project mailbox ...` as the project-scoped mailbox-root wrapper.

That page SHALL make clear that `.houmao/agents/compatibility-profiles/` is optional specialized metadata and is not created by default during `project init`.

#### Scenario: Reader can initialize and interpret a new local Houmao project overlay
- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand that `houmao-mgr project init` creates the local `.houmao/` overlay by default
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DIR` can redirect the overlay directory directly for CI
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only` can keep ambient overlay discovery scoped to the current working directory
- **AND THEN** they understand that `.houmao/agents/compatibility-profiles/` is created only when explicitly enabled
- **AND THEN** they understand that `.houmao/mailbox/` is a project-local mailbox root created only when mailbox workflows are enabled explicitly
- **AND THEN** they understand which files are local-only, including the whole `.houmao/` overlay and `tools/<tool>/auth/`

### Requirement: Repo-owned onboarding docs use the catalog-backed `.houmao` overlay and `.houmao`-only ambient agent-definition defaults
Repo-owned onboarding docs that explain local build and launch workflows SHALL describe the catalog-backed `.houmao` overlay and ambient agent-definition resolution as:

1. explicit CLI `--agent-def-dir`,
2. `HOUMAO_AGENT_DEF_DIR`,
3. the overlay directory selected by `HOUMAO_PROJECT_OVERLAY_DIR`,
4. ambient project-overlay discovery controlled by `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`,
5. default fallback `<cwd>/.houmao/agents`.

Those docs SHALL describe `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override for selecting the overlay directory directly, and SHALL describe `houmao-config.toml` as the discovery anchor within the selected overlay directory.
Those docs SHALL describe `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as the ambient project-overlay discovery selector, where `ancestor` remains the default and `cwd_only` limits lookup to `<cwd>/.houmao/houmao-config.toml`.
Those docs SHALL describe `agents/` as the compatibility projection used when file-tree consumers need a local agent-definition root.
They SHALL NOT describe `.agentsys` as a supported default or fallback path for current workflows.

At minimum, this requirement SHALL apply to:

- `README.md` sections that explain local project initialization and build-based workflows,
- getting-started pages that explain the `.houmao/` overlay and local launch flow,
- current CLI-facing onboarding pages linked from getting-started content.

#### Scenario: Reader sees the catalog-backed `.houmao` overlay and discovery-mode precedence in onboarding docs
- **WHEN** a reader follows the repo-owned onboarding docs for local build and launch
- **THEN** the docs describe the catalog-backed `.houmao` overlay with `houmao-config.toml` as the discovery anchor
- **AND THEN** the docs describe `HOUMAO_PROJECT_OVERLAY_DIR` as the explicit overlay-root selector
- **AND THEN** the docs describe `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as the ambient discovery-mode selector with `ancestor` and `cwd_only`
- **AND THEN** the docs describe ambient agent-definition lookup using `houmao-config.toml` and the default `<cwd>/.houmao/agents`
- **AND THEN** the docs do not present `<cwd>/.agentsys/agents` as a supported fallback

#### Scenario: Reader is not told to preserve `.agentsys` during local setup
- **WHEN** a reader follows the build-based project setup guidance
- **THEN** the docs tell them to initialize or use `.houmao/`
- **AND THEN** the docs do not tell them to create, copy, or retain `.agentsys/agents` as part of the supported setup flow
