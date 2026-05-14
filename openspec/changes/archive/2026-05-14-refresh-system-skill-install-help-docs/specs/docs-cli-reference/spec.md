## ADDED Requirements

### Requirement: System-skills CLI reference distinguishes CLI management from installed-skill help

The CLI reference page `docs/reference/cli/system-skills.md` SHALL state that `houmao-mgr system-skills` is the operator-facing CLI surface for installing, inspecting, and removing packaged Houmao-owned skill projections.

The page SHALL state that prompt-level requests such as `$houmao-touring help` or `$houmao-agent-email-comms help` are answered by installed skills and are not a `houmao-mgr system-skills help` subcommand.

The page SHALL link to `docs/getting-started/system-skills-overview.md` for the narrative explanation of skill-level help.

#### Scenario: Reader does not look for a nonexistent CLI help subcommand
- **WHEN** a reader opens the system-skills CLI reference after hearing about skill help
- **THEN** the page explains that `$<skill> help` is prompt-level installed-skill behavior
- **AND THEN** the page does not present `houmao-mgr system-skills help` as a command
- **AND THEN** the page still documents the real `list`, `status`, `install`, and `uninstall` subcommands

### Requirement: System-skills CLI reference notes the external Skills CLI install path

The CLI reference page `docs/reference/cli/system-skills.md` SHALL mention that users with `npx` and internet access can alternatively install from the GitHub main-branch system-skill collection with `npx skills add https://github.com/igamenovoer/houmao/tree/main/src/houmao/agents/assets/system_skills/`.

That note SHALL keep the rest of the page authoritative for `houmao-mgr system-skills` behavior such as effective-home resolution, named sets, subset skills, symlink/copy projection, status, uninstall, and cleanup of retired skill projections.

#### Scenario: Reader understands the CLI reference boundary
- **WHEN** a reader opens the system-skills CLI reference for installation guidance
- **THEN** they see the external Skills CLI option as adjacent guidance
- **AND THEN** they understand the page's detailed command behavior applies to `houmao-mgr system-skills`
