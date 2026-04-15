## MODIFIED Requirements

### Requirement: Packaged `houmao-project-mgr` skill explains overlay resolution, `.houmao` layout, and bootstrap semantics
The `houmao-project-mgr` skill SHALL document the current project-overlay resolution inputs and precedence, including:

- `HOUMAO_PROJECT_OVERLAY_DIR`
- `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`
- `HOUMAO_AGENT_DEF_DIR`
- ambient `ancestor` versus `cwd_only` discovery behavior

The skill SHALL explain the managed `.houmao/` layout and SHALL distinguish the canonical semantic store from the compatibility projection. At minimum, that layout guidance SHALL cover:

- `houmao-config.toml`
- `catalog.sqlite`
- `content/`
- `agents/` as the compatibility projection materialized from the catalog and managed content
- `runtime/`
- `jobs/`
- `mailbox/`
- `easy/`

The skill SHALL explain the current bootstrap distinction between creating and non-creating flows:

- `project status` uses non-creating resolution and reports `would_bootstrap_overlay` when the selected overlay does not exist yet
- stateful project-aware flows that ensure local roots may bootstrap the selected overlay
- `project easy instance list|get|stop` use non-creating selected-overlay resolution and SHALL be described as requiring an already-existing overlay

The skill SHALL NOT instruct agents to ask whether users want compatibility profiles pre-created, SHALL NOT mention `--with-compatibility-profiles`, and SHALL NOT present `.houmao/agents/compatibility-profiles/` as part of the maintained user-facing layout.

#### Scenario: Reader checks how overlay selection works
- **WHEN** a reader opens the overlay-resolution material referenced by `houmao-project-mgr`
- **THEN** they see the precedence and semantics for `HOUMAO_PROJECT_OVERLAY_DIR`, `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, and `HOUMAO_AGENT_DEF_DIR`
- **AND THEN** they see the distinction between `ancestor` and `cwd_only` ambient discovery

#### Scenario: Reader checks project layout and bootstrap behavior
- **WHEN** a reader opens the layout or lifecycle material referenced by `houmao-project-mgr`
- **THEN** they see `.houmao/catalog.sqlite` and `.houmao/content/` described as the canonical semantic store and managed payload roots
- **AND THEN** they see `.houmao/agents/` described as the compatibility projection rather than the sole canonical source
- **AND THEN** they see that `project status` reports bootstrap intent while `project easy instance list|get|stop` require an existing selected overlay
- **AND THEN** they do not see compatibility-profile bootstrap guidance in the project-overlay lifecycle workflow
