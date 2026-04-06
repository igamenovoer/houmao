## MODIFIED Requirements

### Requirement: Agent definition directory layout documented

The getting-started section SHALL include a page documenting the default Houmao project overlay rooted at `.houmao/` beneath the working directory, including:

- `.houmao/houmao-config.toml`
- `.houmao/.gitignore`
- `.houmao/agents/skills/<skill>/`
- `.houmao/agents/roles/<role>/system-prompt.md`
- `.houmao/agents/presets/<preset>.yaml`
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

That page SHALL explain that named preset files under `.houmao/agents/presets/` carry `role`, `tool`, and `setup` in their content rather than deriving those identities from the directory path.

That page SHALL make clear that `.houmao/agents/compatibility-profiles/` is optional specialized metadata and is not created by default during `project init`.

#### Scenario: Reader can initialize and interpret a new local Houmao project overlay
- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand that `houmao-mgr project init` creates the local `.houmao/` overlay by default
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DIR` can redirect the overlay directory directly for CI
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only` can keep ambient overlay discovery scoped to the current working directory
- **AND THEN** they understand that `.houmao/agents/compatibility-profiles/` is created only when explicitly enabled
- **AND THEN** they understand that `.houmao/mailbox/` is a project-local mailbox root created only when mailbox workflows are enabled explicitly
- **AND THEN** they understand which files are local-only, including the whole `.houmao/` overlay and `tools/<tool>/auth/`
