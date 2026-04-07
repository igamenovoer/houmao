## MODIFIED Requirements

### Requirement: Easy-specialist conceptual guide exists

The getting-started section SHALL include a page at `docs/getting-started/easy-specialists.md` documenting the easy lane as a three-step model: easy specialist, optional easy profile, and easy instance. The page SHALL retain the existing filename so that incoming README and `docs/index.md` cross-links continue to resolve.

The page SHALL explain:

- What an easy-specialist is: a lightweight, project-local agent definition that bundles a role, tool, setup, auth, optional skills, and durable launch configuration into a single named source definition.
- What an easy profile is: a reusable specialist-backed birth-time launch configuration object that targets exactly one specialist and stores defaults for managed-agent identity, working directory, auth override, mailbox configuration, launch posture, durable env records, and prompt overlay. Easy profiles are project-local catalog objects in the same shared launch-profile family that backs explicit recipe-backed launch profiles.
- When to use easy specialist alone, when to use easy specialist plus easy profile, and when to drop down to the explicit recipe + launch-profile lane: easy specialist alone is the recommended path for one-off setups; easy profile is the natural step when the same specialist needs to be relaunched with the same managed-agent identity, workdir, and mailbox each time; the explicit recipe + launch-profile lane is for operators who need fine-grained control over the underlying source recipe.
- The full lifecycle: `specialist create` defines the source template, optional `profile create` captures reusable birth-time defaults over that specialist, `instance launch` creates a running managed agent from either the specialist directly or from an easy profile, and `instance stop` shuts it down.
- Relationship to managed agents: an easy instance IS a managed agent — it appears in `agents list`, can be targeted by `agents prompt`, `agents gateway`, `agents mail`, etc.
- CLI commands: `project easy specialist create|list|get|remove`, `project easy profile create|list|get|remove`, and `project easy instance launch|list|get|stop`, including `instance launch --profile <name>` and the `--profile`/`--specialist` mutual exclusion rule.
- Easy-instance inspection: `instance list` and `instance get` SHALL report the originating easy-profile identity when runtime-backed state makes it resolvable, and SHALL continue to report the originating specialist when available.

The page SHALL include a mermaid diagram showing the three-step easy lane (specialist → optional easy profile → instance → managed agent). The page SHALL NOT use plain-text ASCII art for that diagram.

The comparison at the top of the page SHALL be a three-way comparison that distinguishes easy specialist alone, easy specialist plus easy profile, and explicit recipe plus launch-profile, rather than the previous two-way "easy specialist vs full preset" comparison.

The page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model and to `docs/reference/cli/houmao-mgr.md` for the canonical CLI reference.

The page SHALL be derived from `project/easy.py`, `project/launch_profiles.py`, and `srv_ctrl/commands/project.py` easy-lane command implementations.

#### Scenario: Reader understands the three easy-lane object roles

- **WHEN** a reader opens the easy-specialist guide
- **THEN** they find a clear distinction between easy specialist (the source definition), easy profile (reusable birth-time configuration over one specialist), and easy instance (the runtime object)
- **AND THEN** they understand that easy profiles and explicit launch profiles share one underlying catalog-backed launch-profile object family

#### Scenario: Reader can create a specialist, an easy profile, and launch from the profile

- **WHEN** a reader follows the easy-specialist guide
- **THEN** they find step-by-step commands: `project easy specialist create --name <name> --tool <tool> ...`, then `project easy profile create --name <profile> --specialist <name> ...`, then `project easy instance launch --profile <profile>`
- **AND THEN** they understand that `--profile` and `--specialist` cannot be combined on `instance launch`
- **AND THEN** they understand that when `--profile` is used, the launch derives the source specialist from the stored profile and applies easy-profile defaults before direct CLI overrides

#### Scenario: Reader sees easy-instance inspection report the easy-profile origin

- **WHEN** a reader looks up `project easy instance get` in the guide
- **THEN** the page documents that the inspection output reports both the originating easy-profile and the originating specialist when those identities are resolvable from runtime-backed state

#### Scenario: Reader uses a mermaid diagram for the lane shape

- **WHEN** a reader scans the guide for the easy-lane lifecycle picture
- **THEN** the lifecycle diagram is rendered as a mermaid fenced code block
- **AND THEN** the page does not use plain-text ASCII art for the lifecycle shape

#### Scenario: Reader sees a three-way comparison instead of the old two-way one

- **WHEN** a reader checks the comparison section near the top of the guide
- **THEN** the comparison covers easy specialist, easy specialist plus easy profile, and explicit recipe plus launch-profile
- **AND THEN** the comparison does not present the choice as "easy specialist vs full preset" only

#### Scenario: Reader understands instance lifecycle

- **WHEN** a reader wants to manage easy instances
- **THEN** the page documents `instance list` for discovery, `instance get` for detailed state, and `instance stop` for shutdown
- **AND THEN** the page explains that instances are tracked in the shared registry like any other managed agent
