## ADDED Requirements

### Requirement: Runtime-managed session control uses the `realm_controller` module surface
The repo-owned runtime SHALL expose its direct module entrypoint, canonical source-path references, and canonical runtime documentation under the `gig_agents.agents.realm_controller` / `realm_controller` name rather than `brain_launch_runtime`.

This rename SHALL preserve the existing runtime subcommands and their current session-control behavior.

#### Scenario: Module-form runtime invocation uses `realm_controller`
- **WHEN** a developer invokes the runtime through its documented module form
- **THEN** the canonical module path is `gig_agents.agents.realm_controller`
- **AND THEN** the runtime continues to expose the existing subcommands `build-brain`, `start-session`, `send-prompt`, `send-keys`, `mail`, and `stop-session`

#### Scenario: Canonical runtime docs and source mappings use `realm_controller`
- **WHEN** a reader navigates active runtime docs or repo-owned source mappings for the runtime
- **THEN** those docs and mappings use `realm_controller` as the canonical runtime name
- **AND THEN** active guidance does not present `brain_launch_runtime` as the preferred runtime surface
