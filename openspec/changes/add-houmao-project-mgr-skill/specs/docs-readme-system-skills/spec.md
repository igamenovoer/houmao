## MODIFIED Requirements

### Requirement: README usage section introduces system skills
The `README.md` usage section SHALL include a subsection introducing the system-skills surface. The subsection SHALL appear after the "Subsystems at a Glance" table and before the "Full Documentation" section.

The subsection SHALL explain that Houmao installs packaged skills into agent tool homes so that agents can drive management tasks through their native skill interface without requiring the operator to invoke `houmao-mgr` manually.

The subsection SHALL list the seven non-mailbox packaged skill families:
- `houmao-project-mgr` — project overlay lifecycle, project layout, and project-scoped launch-profile and easy-instance inspection routing
- `houmao-specialist-mgr` — specialist authoring plus specialist-scoped launch and stop entry
- `houmao-credential-mgr` — project-local credential management
- `houmao-agent-definition` — low-level role and preset definition management
- `houmao-agent-instance` — managed agent instance lifecycle
- `houmao-agent-messaging` — prompt, queue, raw-input, mailbox routing, and reset-context guidance for already-running managed agents
- `houmao-agent-gateway` — gateway lifecycle, gateway discovery, wakeups, and notifier guidance for attached managed agents

The subsection SHALL explain that `agents join` and `agents launch` auto-install the packaged user-control, agent-messaging, and agent-gateway skills into managed homes by default, which means the managed user-control install now includes `houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, and `houmao-agent-definition`, while explicit `houmao-mgr system-skills install` into an external tool home can add the broader CLI-default skill selection that also includes `houmao-agent-instance`.

The subsection SHALL show a brief current `houmao-mgr system-skills install` example for explicit external tool homes that relies on the CLI-default selection by omitting both `--set` and `--skill`.

The subsection SHALL link to `docs/reference/cli/system-skills.md` for the full reference.

#### Scenario: Reader discovers system skills from the README

- **WHEN** a reader scans the README usage section
- **THEN** they find a subsection describing the system-skills surface
- **AND THEN** they see the seven non-mailbox packaged skill families listed with brief descriptions
- **AND THEN** they see that `houmao-project-mgr` is presented as the project lifecycle and layout skill

#### Scenario: Reader can distinguish managed auto-install from external CLI-default install

- **WHEN** a reader wants to understand which Houmao skills appear inside managed homes versus an explicit external tool home
- **THEN** the README explains that managed launch and join auto-install the user-control, messaging, and gateway skills
- **AND THEN** it explains that the managed `user-control` set now includes `houmao-project-mgr`
- **AND THEN** it explains that external `system-skills install` can add the broader CLI-default selection that also includes `houmao-agent-instance`

#### Scenario: Reader can install system skills into an external tool home with current CLI syntax

- **WHEN** a reader wants to prepare an external tool home with Houmao skills
- **THEN** the README shows a `houmao-mgr system-skills install` example with `--tool` and `--home` flags and no stale `--default` flag
- **AND THEN** the example links to the full reference for additional options
