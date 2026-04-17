## ADDED Requirements

### Requirement: System-skills overview guide explains uninstall behavior
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL mention `houmao-mgr system-skills uninstall` as the supported way to remove the current Houmao-owned system-skill surface from resolved external or project-scoped tool homes.

The guide SHALL state that uninstall removes all current catalog-known Houmao system skills for the resolved tool home and does not mirror install's `--skill` or `--skill-set` selection behavior.

The guide SHALL include at least one uninstall example for a single tool and MAY point readers to `docs/reference/cli/system-skills.md` for the full flag and output surface.

The guide SHALL explain the removal boundary at a narrative level: uninstall removes current Houmao-owned skill projection paths and preserves unrelated user skills, parent roots, legacy paths, and obsolete install-state files.

#### Scenario: Reader sees how to remove installed system skills
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide mentions `houmao-mgr system-skills uninstall`
- **AND THEN** it explains that uninstall removes all current known Houmao system skills for the resolved tool home

#### Scenario: Reader understands uninstall differs from selective install
- **WHEN** a reader compares install and uninstall guidance in the overview guide
- **THEN** the guide explains that install can select sets or explicit skills
- **AND THEN** it explains that uninstall is intentionally all-current-known-Houmao-skills for the target home

#### Scenario: Reader sees uninstall's deletion boundary
- **WHEN** a reader checks the overview guide's uninstall guidance
- **THEN** the guide states that unrelated user skills, parent roots, legacy paths, and obsolete install-state files are outside the uninstall deletion boundary
