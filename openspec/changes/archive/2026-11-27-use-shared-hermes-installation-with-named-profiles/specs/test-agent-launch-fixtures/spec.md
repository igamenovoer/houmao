# Spec Delta

## ADDED Requirements

### Requirement: Managed Hermes Fixtures Qualify Shared Prepared Installations

The managed Hermes fixture SHALL support multiple workers in one explicitly selected, test-owned execution context and prepared Hermes root while tracking a separate profile, workspace, project link, and runtime generation per worker. The qualification SHALL record provider version and dependency, lifecycle, and authority evidence without secrets.

#### Scenario: Fresh Worker Starts Reuse the Prepared Runtime

- **WHEN** a fixture prepares one installation and launches named-profile workers from two separate projects in that execution context
- **THEN** qualification checks one current gateway and prepared dependency selection across Service, TUI, and Headless
- **AND THEN** evidence confirms worker launch, a managed prompt, and exact relaunch perform no dependency installation or private environment rebuild

#### Scenario: Workers Preserve Distinct Authority on the Shared Host

- **WHEN** two live profiles run simultaneous work with distinct synthetic credentials and approval postures
- **THEN** qualification verifies native credential and permission selection, session attribution, and signed managed-self operations for each profile
- **AND THEN** it verifies that copied selectors, sibling activity, and stale caller evidence cannot control or sign as the other profile

#### Scenario: One Profile Stops, Recovers, and Is Removed

- **WHEN** a fixture stops, exactly relaunches, then explicitly removes one worker
- **THEN** it verifies stop retains its home and link, relaunch uses the saved native conversation, and cleanup removes both owned artifacts
- **AND THEN** shared gateway and sibling readiness are verified before the fixture separately retires its test-owned host
