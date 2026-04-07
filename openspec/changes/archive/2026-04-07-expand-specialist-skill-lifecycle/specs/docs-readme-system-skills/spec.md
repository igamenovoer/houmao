## MODIFIED Requirements

### Requirement: README usage section introduces system skills
The `README.md` usage section SHALL include a subsection introducing the system-skills surface. The subsection SHALL appear after the "Subsystems at a Glance" table and before the "Full Documentation" section.

The subsection SHALL explain that Houmao installs packaged skills into agent tool homes so that agents can drive management tasks through their native skill interface without requiring the operator to invoke `houmao-mgr` manually.

The subsection SHALL list the four non-mailbox packaged skill families:
- `houmao-manage-specialist` — specialist authoring plus specialist-scoped launch and stop entry
- `houmao-manage-credentials` — project-local credential management
- `houmao-manage-agent-definition` — low-level role and preset definition management
- `houmao-manage-agent-instance` — managed agent instance lifecycle

The subsection SHALL note that `agents join` and `agents launch` auto-install these skills by default, and SHALL show a brief `system-skills install --default` example for explicit external tool homes.

The subsection SHALL link to `docs/reference/cli/system-skills.md` for the full reference.

#### Scenario: Reader discovers system skills from the README

- **WHEN** a reader scans the README usage section
- **THEN** they find a subsection describing the system-skills surface
- **AND THEN** they see the four non-mailbox skill families listed with brief descriptions
- **AND THEN** they see that `houmao-manage-specialist` is not described as CRUD-only

#### Scenario: Reader can install system skills into an external tool home

- **WHEN** a reader wants to prepare an external tool home with Houmao skills
- **THEN** the README shows a `houmao-mgr system-skills install --default` example with `--tool` and `--home` flags
- **AND THEN** the example links to the full reference for additional options
