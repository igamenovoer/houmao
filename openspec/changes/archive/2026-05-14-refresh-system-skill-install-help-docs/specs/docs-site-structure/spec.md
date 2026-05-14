## ADDED Requirements

### Requirement: Docs index starts installed users on the current agent-driven install path

The docs landing page `docs/index.md` SHALL point installed users toward the current recommended agent-driven setup path.

For installed users with `npx` and internet access, the docs index SHALL mention installing system skills with `npx skills add` against the GitHub main-branch `system_skills/` collection or link to guidance that does so.

The docs index SHALL still route readers to `houmao-mgr system-skills install` or the system-skills overview/reference when they need offline, package-local, explicit-home, named-set, subset-skill, symlink/copy, or cleanup behavior.

The docs index SHALL mention invoking `houmao-touring` or asking an installed system skill for help as the next agent-driven step.

#### Scenario: Installed user sees current start guidance
- **WHEN** an installed user opens `docs/index.md`
- **THEN** the "where to start" table or equivalent intro points them at the current system-skill installation guidance
- **AND THEN** the guidance does not imply that `houmao-mgr system-skills install --tool claude` is the only recommended first step
- **AND THEN** the guidance points them toward `houmao-touring` or explicit skill help after installation
