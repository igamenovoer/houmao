## Why

Managed agents currently launch from the selected role prompt plus any profile-owned prompt overlay, but they are not explicitly told that they are running under Houmao management, what their managed identity is, or which Houmao-owned interfaces are authoritative for Houmao-specific work. That leaves too much room for ad hoc probing and inconsistent behavior across launch surfaces.

Houmao needs one default managed-launch prompt header that gives agents the right orientation without naming unstable individual packaged guidance entries, while still giving operators an explicit way to disable that injection for minimal or experimental launches.

## What Changes

- Add a default-on managed prompt header that is prepended to the effective launch prompt for Houmao-managed launches.
- Make that header general-purpose: it identifies the managed agent, states that `houmao-mgr` is the canonical direct interface to the Houmao system, and tells the agent to prefer Houmao-owned guidance and supported system interfaces for Houmao-related work without naming specific packaged guidance entries.
- Apply the managed header after launch-profile prompt overlay resolution and before backend-specific prompt injection so relaunch and resume continue to use one persisted effective launch prompt.
- Add operator-facing controls to disable or force the managed header at launch time, plus reusable launch-profile-owned policy for the profile-backed launch lanes.
- Ensure compatibility-generated launch prompts and managed runtime relaunch paths use the same managed-header composition rules as direct local launch.
- Update launch-profile and CLI documentation to explain the managed header, its precedence, and its opt-out behavior.

## Capabilities

### New Capabilities
- `managed-launch-prompt-header`: Define the default managed-launch prompt header, its general content contract, composition order, persistence, and relaunch behavior.

### Modified Capabilities
- `agent-launch-profiles`: Allow the shared launch-profile object family to store an optional managed-header policy as reusable birth-time launch configuration.
- `brain-launch-runtime`: Update effective launch-prompt composition and compatibility profile generation so managed launches can inject the managed header even when the source role prompt is empty.
- `houmao-mgr-agents-launch`: Add one-shot launch-time managed-header override controls for direct managed launch.
- `houmao-mgr-project-agents-launch-profiles`: Add explicit launch-profile create and update controls for managed-header policy.
- `houmao-mgr-project-easy-cli`: Add easy-profile create support for stored managed-header policy and easy-instance launch support for one-shot managed-header override.
- `docs-launch-profiles-guide`: Document the managed header as part of launch-prompt composition and explain its precedence and opt-out behavior.
- `docs-easy-specialist-guide`: Document the easy-lane managed-header controls where easy profiles and easy instance launch are described.
- `docs-cli-reference`: Document the new managed-header launch and profile flags in the `houmao-mgr` reference.

## Impact

- Affected code includes local launch orchestration, brain build inputs, runtime launch-plan composition, project catalog launch-profile storage, easy-lane profile creation and instance launch, and compatibility launch projection.
- Launch-profile catalog state gains one additional optional launch-owned field for managed-header policy.
- Promptless managed launches change behavior by default because the effective launch prompt can become non-empty even when the source role prompt is empty; the new opt-out is the supported escape hatch.
- Documentation for launch profiles, easy profiles, and CLI option tables must be updated together so the new policy and precedence stay coherent.
