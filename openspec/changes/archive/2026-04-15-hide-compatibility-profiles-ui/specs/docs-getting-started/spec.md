## MODIFIED Requirements

### Requirement: Agent definition directory layout documented

The getting-started section SHALL include a page documenting the default Houmao project overlay rooted at `.houmao/` beneath the working directory, including:

- `.houmao/houmao-config.toml`
- `.houmao/.gitignore`
- `.houmao/agents/skills/<skill>/`
- `.houmao/agents/roles/<role>/system-prompt.md`
- `.houmao/agents/presets/<recipe>.yaml`
- `.houmao/agents/launch-profiles/<profile>.yaml`
- `.houmao/agents/tools/<tool>/adapter.yaml`
- `.houmao/agents/tools/<tool>/setups/<setup>/`
- `.houmao/agents/tools/<tool>/auth/<auth>/`
- optional `.houmao/mailbox/`

That page SHALL explain the purpose of each subdirectory and SHALL make clear that the `.houmao/` overlay is local-only by default.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override for selecting the overlay directory directly in CI or controlled automation.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as an ambient discovery-mode env where `ancestor` remains the default and `cwd_only` restricts ambient lookup to `<cwd>/.houmao/houmao-config.toml`.

That page SHALL distinguish:

- `project agents ...` as the low-level filesystem-oriented project source surface,
- `project easy ...` as the higher-level specialist, easy-profile, and instance UX,
- `project mailbox ...` as the project-scoped mailbox-root wrapper.

That page SHALL explain that the canonical low-level source object is the named recipe and that recipe files projected under `.houmao/agents/presets/` carry `role`, `tool`, and `setup` in their content rather than deriving those identities from the directory path. The page SHALL state that `project agents recipes ...` is the canonical CLI surface for those resources and that `project agents presets ...` remains a compatibility alias that operates on the same files.

That page SHALL explain that reusable birth-time launch profiles project under `.houmao/agents/launch-profiles/<profile>.yaml`, that easy profiles and explicit launch profiles share the same underlying catalog model, and that the explicit lane is administered through `project agents launch-profiles ...`.

That page SHALL NOT document `.houmao/agents/compatibility-profiles/` as a user-facing project-layout directory or project-init option.

That page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model when readers want to understand the easy-versus-explicit lane split rather than just the directory layout.

#### Scenario: Reader can initialize and interpret a new local Houmao project overlay
- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand that `houmao-mgr project init` creates the local `.houmao/` overlay by default
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DIR` can redirect the overlay directory directly for CI
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only` can keep ambient overlay discovery scoped to the current working directory
- **AND THEN** they understand that recipe files projected under `.houmao/agents/presets/` carry `role`, `tool`, and `setup` in their content, that `project agents recipes ...` is the canonical authoring surface, and that `project agents presets ...` remains a compatibility alias
- **AND THEN** they understand that launch-profile files projected under `.houmao/agents/launch-profiles/` are reusable birth-time configuration shared between easy and explicit authoring lanes
- **AND THEN** they understand that `.houmao/mailbox/` is a project-local mailbox root created only when mailbox workflows are enabled explicitly
- **AND THEN** they understand which files are local-only, including the whole `.houmao/` overlay and `tools/<tool>/auth/`
- **AND THEN** they do not see compatibility-profile bootstrap guidance as part of the maintained project-init workflow

#### Scenario: Reader is sent to the launch-profiles guide for the conceptual model
- **WHEN** a reader needs to understand the easy-versus-explicit launch-profile lane split rather than the projection layout
- **THEN** the agent-definition page links them to `docs/getting-started/launch-profiles.md`
