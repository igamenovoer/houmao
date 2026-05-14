## ADDED Requirements

### Requirement: README distinguishes Skills CLI install from Houmao system-skills install

The README system-skill guidance SHALL present `npx skills add https://github.com/igamenovoer/houmao/tree/main/src/houmao/agents/assets/system_skills/` as the recommended install path when `npx` is available and the target machine has internet access.

The README SHALL present `houmao-mgr system-skills install` as the preferred path when `npx` is unavailable, internet access is unavailable, the user is working from an installed Houmao package, or the user needs customization such as named sets, subset skills, explicit homes, symlink/copy projection, or retired-skill cleanup.

The README SHALL point the external Skills CLI at the `system_skills/` collection directory rather than at an individual skill path, so the user can choose the packaged skill or skills to install.

#### Scenario: Reader sees the recommended internet path
- **WHEN** a reader scans the README's agent-driven setup guidance
- **THEN** they see an `npx skills add` command pointed at the GitHub main-branch `system_skills/` directory
- **AND THEN** the surrounding text qualifies that path as recommended when `npx` and internet access are available

#### Scenario: Reader sees when to use Houmao installer
- **WHEN** a reader needs offline, package-local, selected-set, selected-skill, explicit-home, symlink/copy, or cleanup behavior
- **THEN** the README routes them to `houmao-mgr system-skills install`
- **AND THEN** the README does not imply that the external Skills CLI owns Houmao-specific projection or cleanup behavior

### Requirement: README mentions explicit read-only skill help

The README SHALL tell users that each installed Houmao system skill supports an explicit read-only help request before it performs a workflow.

The README SHALL include at least one prompt-level example such as `$houmao-touring help` or `$houmao-agent-email-comms help`.

The README SHALL distinguish skill-level help from the `houmao-mgr system-skills install` CLI surface.

#### Scenario: Reader discovers skill help from README
- **WHEN** a reader scans the README system-skill guidance
- **THEN** they see that installed skills can answer explicit read-only help requests
- **AND THEN** they see at least one `$<skill> help` example
- **AND THEN** the README does not imply that help runs commands or mutates Houmao state
