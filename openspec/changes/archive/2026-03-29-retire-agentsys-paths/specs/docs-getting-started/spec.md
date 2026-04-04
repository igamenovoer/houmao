## ADDED Requirements

### Requirement: Repo-owned onboarding docs use the catalog-backed `.houmao` overlay and `.houmao`-only ambient agent-definition defaults
Repo-owned onboarding docs that explain local build and launch workflows SHALL describe the catalog-backed `.houmao` overlay and ambient agent-definition resolution as:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. nearest ancestor `.houmao/houmao-config.toml`,
4. default fallback `<cwd>/.houmao/agents`.

Those docs SHALL describe `.houmao/houmao-config.toml` as the project-discovery anchor for the catalog-backed overlay and `.houmao/agents/` as the compatibility projection used when file-tree consumers need a local agent-definition root. They SHALL NOT describe `.agentsys` as a supported default or fallback path for current workflows.

At minimum, this requirement SHALL apply to:

- `README.md` sections that explain local project initialization and build-based workflows,
- getting-started pages that explain the `.houmao/` overlay and local launch flow,
- current CLI-facing onboarding pages linked from getting-started content.

#### Scenario: Reader sees the catalog-backed `.houmao` overlay and `.houmao`-only precedence in onboarding docs
- **WHEN** a reader follows the repo-owned onboarding docs for local build and launch
- **THEN** the docs describe the catalog-backed `.houmao` overlay with `.houmao/houmao-config.toml` as the discovery anchor
- **AND THEN** the docs describe ambient agent-definition lookup using `.houmao/houmao-config.toml` and the default `<cwd>/.houmao/agents`
- **AND THEN** the docs do not present `<cwd>/.agentsys/agents` as a supported fallback

#### Scenario: Reader is not told to preserve `.agentsys` during local setup
- **WHEN** a reader follows the build-based project setup guidance
- **THEN** the docs tell them to initialize or use `.houmao/`
- **AND THEN** the docs do not tell them to create, copy, or retain `.agentsys/agents` as part of the supported setup flow
