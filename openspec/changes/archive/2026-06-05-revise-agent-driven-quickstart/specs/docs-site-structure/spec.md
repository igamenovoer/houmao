## MODIFIED Requirements

### Requirement: Docs index opens with a brief intro and audience navigation

The `docs/index.md` file SHALL open with a short introductory block (2-3 sentences) describing what Houmao is and who the site is for (primarily installed users, with developer and contributor material available). Immediately after the intro, the file SHALL include a "where to start" table with at minimum three audience rows: installed user, from-source developer, and contributor. Each row SHALL name the audience and point to its recommended starting resource.

The installed-user row SHALL point readers toward installing Houmao system skills, starting their CLI agent in the target project, and invoking `houmao-touring`. The from-source developer row SHALL still point to the quickstart guide, but it SHALL describe that page as the agent-driven first-run guide with source-checkout launcher notes rather than as a manual build-brain command walkthrough.

#### Scenario: Installed user lands on docs index

- **WHEN** an installed user opens `docs/index.md`
- **THEN** they read a 2-3 sentence description of what Houmao is before encountering any link list
- **AND THEN** they see a "where to start" entry pointing them toward the skill-driven `houmao-touring` path

#### Scenario: From-source developer lands on docs index

- **WHEN** a developer working from a source checkout opens `docs/index.md`
- **THEN** the "where to start" table identifies them and points them to the quickstart guide
- **AND THEN** the row makes clear that the quickstart is agent-driven and includes source-checkout launcher notes

#### Scenario: Contributor lands on docs index

- **WHEN** a contributor opens `docs/index.md`
- **THEN** the "where to start" table identifies them and points them to CLAUDE.md or AGENTS.md

#### Scenario: Existing link sections are preserved

- **WHEN** a reader scrolls past the intro block
- **THEN** all previously existing Getting Started, Reference, and Developer Guides link sections are intact with no links removed
