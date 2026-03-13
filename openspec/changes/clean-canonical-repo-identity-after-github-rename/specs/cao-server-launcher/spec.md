## ADDED Requirements

### Requirement: User-facing launcher CLI uses the Houmao name
The repository SHALL publish the supported user-facing CAO launcher CLI under the name `houmao-cao-server`.

Repo-owned docs, examples, scripts, and help text SHALL teach `houmao-cao-server` as the current launcher command and SHALL NOT present `gig-cao-server` as a current user-facing launcher surface.

#### Scenario: Launcher command examples use the canonical binary name
- **WHEN** a developer follows a repo-owned launcher example or help page
- **THEN** the example uses `houmao-cao-server`
- **AND THEN** it does not instruct the developer to run `gig-cao-server`
