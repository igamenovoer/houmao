## ADDED Requirements

### Requirement: Easy-specialist guide documents specialist editing
The easy-specialist guide SHALL document how to edit an existing easy specialist with `houmao-mgr project easy specialist set --name <specialist> ...`.

The guide SHALL explain that specialist `set` preserves unspecified stored source-definition fields, while `project easy specialist create --name <specialist> --tool <tool> ... --yes` performs same-name replacement with create semantics and may clear omitted optional fields.

The guide SHALL include at least one example that changes skill bindings without removing and recreating the specialist.

The guide SHALL state that specialist edits affect future launches or rebuilds from that specialist and do not mutate already-running managed agents in place.

#### Scenario: Reader can edit a specialist skill list without recreating it
- **WHEN** a reader opens the easy-specialist guide
- **THEN** they find an example using `project easy specialist set --name <specialist>` to add or remove a skill binding
- **AND THEN** they learn that manual remove/recreate is not required for ordinary specialist source-definition edits

#### Scenario: Reader understands specialist replacement semantics
- **WHEN** a reader opens the specialist management guidance
- **THEN** the guide explains that `create --yes` replaces the same-name specialist with create semantics
- **AND THEN** the guide distinguishes replacement from patching through `specialist set`

#### Scenario: Reader understands running-agent boundary
- **WHEN** a reader checks the specialist editing guidance
- **THEN** the guide states that editing the specialist source affects future launches or rebuilds
- **AND THEN** it does not imply that already-running managed agents are updated in place
