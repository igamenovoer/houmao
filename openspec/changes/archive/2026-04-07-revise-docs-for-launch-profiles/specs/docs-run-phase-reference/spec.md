## MODIFIED Requirements

### Requirement: LaunchPlan composition documented

The run-phase reference SHALL include a page documenting `LaunchPlan` composition: how `build_launch_plan()` takes a `LaunchPlanRequest` (brain_manifest + role_package + backend + working_directory) and produces a `LaunchPlan` with backend-specific launch arguments. Content SHALL be derived from `launch_plan.py` docstrings.

The page SHALL state that the brain manifest carries launch-profile-derived inputs into runtime launch resolution when the launch originated from a reusable launch profile, including:

- effective auth selection,
- operator prompt-mode intent,
- durable non-secret env records,
- declarative mailbox configuration,
- managed-agent identity defaults,
- prompt-overlay-composed effective role prompt.

The page SHALL state that the build manifest and runtime launch metadata preserve secret-free launch-profile provenance sufficient for inspection and replay, including whether the birth-time config came from an easy profile or an explicit launch profile, and the originating profile name when available.

The page SHALL state that runtime `LaunchPlan` is derived and ephemeral and SHALL NOT be presented as a user-authored object.

The page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model that ties launch profiles to the run-phase composition pipeline.

#### Scenario: Reader understands launch plan resolution

- **WHEN** a reader opens the launch-plan page
- **THEN** they find the `LaunchPlanRequest` fields, the resolution logic (env vars, launch overrides, mailbox bindings, role injection), and the resulting `LaunchPlan` structure

#### Scenario: Reader understands how launch-profile inputs flow into runtime launch resolution

- **WHEN** a reader opens the launch-plan page and looks at how a launch-profile-backed launch is resolved
- **THEN** the page explains that auth selection, operator prompt-mode intent, durable env records, declarative mailbox configuration, managed-agent identity defaults, and the prompt-overlay-composed effective role prompt come through the manifest from the originating launch profile
- **AND THEN** the page explains that launch-profile provenance is preserved in secret-free form on the build manifest and runtime launch metadata
