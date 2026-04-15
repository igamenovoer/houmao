## ADDED Requirements

### Requirement: System-skills overview mentions Copilot installation
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL mention Copilot as a supported explicit external-home installation target for Houmao-owned system skills.

The guide SHALL explain that omitted-home Copilot installs land under `.github/skills/` in the current repository, while explicit personal installs can target `~/.copilot` with `--home ~/.copilot`.

The guide SHALL distinguish Copilot skill discovery from local Houmao runtime availability: Copilot surfaces may discover repository skills, but operational use of Houmao management skills requires an environment where `houmao-mgr` and the relevant local project, tmux, gateway, mailbox, or runtime resources are available.

#### Scenario: Reader sees Copilot in explicit install guidance
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide includes Copilot in the explicit external install guidance
- **AND THEN** it explains the `.github/skills/` default projection path for repository-local Copilot skills

#### Scenario: Reader understands Copilot runtime caveat
- **WHEN** a reader reviews Copilot system-skill guidance
- **THEN** the guide states that discoverability does not guarantee local Houmao runtime resources are available
- **AND THEN** it points readers to local or appropriately provisioned environments for operational Houmao skill use
