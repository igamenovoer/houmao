## Why

Several demo and tutorial packs still depend on legacy recipe and blueprint launch wiring after the agent-definition model moved to presets, setups, and auth bundles. That leaves the demo agent-launch path broken across multiple packs even when the only immediate need is to get the demo process to launch successfully.

## What Changes

- Restore demo agent-launch flows for the affected demo and tutorial packs against the current preset/setup/auth agent-definition model.
- Remove launch-path dependencies on legacy `blueprints/` and `brains/brain-recipes/` trees where they still block demo startup, while allowing compatibility-only adapters where that keeps the repair narrow.
- Update demo-owned runtime helpers, CLI invocations, and tracked launch inputs so demo startup resolves through current preset-backed launch/build surfaces.
- Limit this change to launch-path recovery only. **BREAKING** demo packs MAY continue to have non-launch behavioral gaps after startup; mailbox, reporting, scripted interaction, and other post-launch functionality are explicitly deferred.

## Capabilities

### New Capabilities
- `demo-agent-launch-recovery`: defines the scoped launch-only repair contract for demo and tutorial packs that must start agents successfully against the current preset-backed agent-definition model.

### Modified Capabilities
<!-- None. This change introduces a temporary cross-cutting launch-recovery contract rather than editing every existing demo capability in one pass. -->

## Impact

- Affected code: `src/houmao/demo/**`, selected `scripts/demo/**` helper scripts, and any legacy runtime-helper surfaces still invoked by those demos for agent startup.
- Affected launch inputs: tracked demo parameters, config files, and helper-generated launch arguments that still reference recipes, blueprints, or deprecated build flags.
- Affected workflows: demo smoke/launch flows for packs such as shared TUI tracking, mailbox/tutorial demos, gateway demos, passive/server validation demos, and other script-driven demo launchers identified during implementation.
