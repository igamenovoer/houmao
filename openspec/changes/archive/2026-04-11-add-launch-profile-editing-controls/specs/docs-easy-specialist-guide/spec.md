## ADDED Requirements

### Requirement: Easy-specialist guide documents easy-profile editing
The easy-specialist guide SHALL document how to edit an existing easy profile with `houmao-mgr project easy profile set --name <profile> ...`.

The guide SHALL explain that easy-profile `set` preserves unspecified stored defaults, while `project easy profile create --name <profile> --specialist <specialist> --yes` performs same-lane replacement and clears omitted optional defaults.

The guide SHALL state that easy-profile replacement cannot replace an explicit launch profile that happens to use the same name.

#### Scenario: Reader can edit an easy profile without removing it
- **WHEN** a reader opens the easy-profile section of the easy-specialist guide
- **THEN** they find an example using `project easy profile set --name <profile>`
- **AND THEN** they learn that manual remove/recreate is not required for ordinary stored default changes

#### Scenario: Reader understands easy-profile replacement semantics
- **WHEN** a reader opens the easy-profile management guidance
- **THEN** the guide explains that `create --yes` replaces a same-lane easy profile
- **AND THEN** the guide explains that omitted optional fields are cleared during replacement
