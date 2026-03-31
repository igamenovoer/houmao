## ADDED Requirements

### Requirement: cli.md moves to cli/index.md
The module-level CLI entry points document SHALL be relocated from `docs/reference/cli.md` to `docs/reference/cli/index.md` so it serves as the section hub page under MkDocs Material's `navigation.indexes` feature. Content SHALL remain equivalent, with deprecated entrypoint references isolated into a clearly labeled "Deprecated Entrypoints" section.

#### Scenario: cli.md relocated
- **WHEN** the mkdocs site is built
- **THEN** `docs/reference/cli/index.md` SHALL exist and `docs/reference/cli.md` SHALL NOT exist

#### Scenario: Deprecated entrypoints section isolated
- **WHEN** a user reads `cli/index.md`
- **THEN** `houmao-cli` and `houmao-cao-server` references SHALL appear in a dedicated "Deprecated Entrypoints" section separate from current CLI surfaces

### Requirement: realm_controller.md merged into run-phase/session-lifecycle.md
Unique content from `docs/reference/realm_controller.md` (high-level orchestration overview, CLI surface note, role injection summary) SHALL be folded into `docs/reference/run-phase/session-lifecycle.md`. The original `realm_controller.md` SHALL be deleted. Duplicated content SHALL appear only once in the merged result.

#### Scenario: Merge eliminates duplicate
- **WHEN** the merge is complete
- **THEN** `docs/reference/realm_controller.md` SHALL NOT exist
- **THEN** `docs/reference/run-phase/session-lifecycle.md` SHALL contain all unique content from the former file

#### Scenario: No content loss in merge
- **WHEN** content is merged
- **THEN** every unique concept from `realm_controller.md` not already present in `session-lifecycle.md` SHALL appear in the merged file

### Requirement: send-keys reference relocated to agents operations
`docs/reference/realm_controller_send_keys.md` SHALL be moved to `docs/reference/agents/operations/send-keys.md`. All internal cross-references to the old path SHALL be updated.

#### Scenario: send-keys file relocated
- **WHEN** the move is complete
- **THEN** `docs/reference/agents/operations/send-keys.md` SHALL exist and `docs/reference/realm_controller_send_keys.md` SHALL NOT exist

### Requirement: managed agent API reference relocated to agents contracts
`docs/reference/managed_agent_api.md` SHALL be moved to `docs/reference/agents/contracts/api.md`. All internal cross-references to the old path SHALL be updated.

#### Scenario: managed agent API file relocated
- **WHEN** the move is complete
- **THEN** `docs/reference/agents/contracts/api.md` SHALL exist and `docs/reference/managed_agent_api.md` SHALL NOT exist

### Requirement: Archived stub deleted
`docs/reference/houmao_server_agent_api_live_suite.md` SHALL be deleted. Any references to it in index pages SHALL be removed or redirected to `managed_agent_api.md` (at its new location).

#### Scenario: Stub file removed
- **WHEN** the deletion is complete
- **THEN** `docs/reference/houmao_server_agent_api_live_suite.md` SHALL NOT exist
- **THEN** no other documentation file SHALL contain a broken link to the deleted file

### Requirement: Internal cross-references updated
All markdown files that reference moved, merged, or deleted files SHALL have their link paths updated to reflect the new locations. The mkdocs build SHALL produce zero broken-link warnings when run with strict mode.

#### Scenario: No broken internal links
- **WHEN** `mkdocs build --strict` is run after all changes
- **THEN** the build SHALL complete with zero link-related warnings or errors

### Requirement: houmao_server_pair.md stays at reference root
`docs/reference/houmao_server_pair.md` SHALL remain at the reference root as a top-level foundational document. It SHALL NOT be moved.

#### Scenario: Pair doc stays at root
- **WHEN** the restructure is complete
- **THEN** `docs/reference/houmao_server_pair.md` SHALL still exist at its current location
