## MODIFIED Requirements

### Requirement: Removing a project skill registration protects referenced specialists
`houmao-mgr project skills remove --name <name>` SHALL refuse to remove a registered project skill while that skill is still referenced by one or more persisted specialist definitions or by one or more stored launch-profile registered skill refs.

Launch-profile private path-backed skills SHALL NOT count as project skill registry references because they are not project skill registrations.

Once no persisted specialist and no stored launch profile references that registered project skill by name, `project skills remove` SHALL remove the canonical project skill entry from `.houmao/content/skills/`.

#### Scenario: Removing a specialist-referenced project skill fails clearly
- **WHEN** project skill `notes` is registered
- **AND WHEN** specialist `researcher` still binds project skill `notes`
- **AND WHEN** an operator runs `houmao-mgr project skills remove --name notes`
- **THEN** the command fails clearly
- **AND THEN** the canonical project skill entry remains present

#### Scenario: Removing a launch-profile-referenced project skill fails clearly
- **WHEN** project skill `notes` is registered
- **AND WHEN** launch profile `reviewer-a` stores registered skill ref `notes`
- **AND WHEN** an operator runs `houmao-mgr project skills remove --name notes`
- **THEN** the command fails clearly
- **AND THEN** the canonical project skill entry remains present
- **AND THEN** the error identifies the launch profile reference

#### Scenario: Removing a project skill is allowed when only private path skills share its name
- **WHEN** project skill `notes` is registered
- **AND WHEN** launch profile `reviewer-a` stores private skill source `/repo/profile-skills/notes`
- **AND WHEN** no specialist or launch profile registered skill ref references project skill `notes`
- **AND WHEN** an operator runs `houmao-mgr project skills remove --name notes`
- **THEN** the command removes project skill `notes`
- **AND THEN** launch profile `reviewer-a` still stores its private path-backed skill source
