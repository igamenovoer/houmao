## REMOVED Requirements

### Requirement: Interactive demo session startup
**Reason**: The repository is retiring `scripts/demo/cao-interactive-full-pipeline-demo/` as an active CAO-era operator workflow.
**Migration**: Use `scripts/demo/houmao-server-interactive-full-pipeline-demo/` for the maintained interactive full-pipeline walkthrough. Shared helper modules preserved for other packs are outside this retired capability.

### Requirement: Follow-up demo commands SHALL reuse the persisted startup variant
**Reason**: This persisted follow-up command contract only applied to the retired interactive CAO demo pack.
**Migration**: Use the maintained Houmao-server interactive demo's persisted run-state contract instead of the removed CAO demo workflow.

### Requirement: Verification artifacts SHALL preserve the selected demo variant
**Reason**: The verification contract is specific to the retired CAO interactive demo pack.
**Migration**: Use the maintained Houmao-server interactive demo verification flow for supported interactive walkthrough coverage.

### Requirement: Multi-turn prompt driving against a live session
**Reason**: This prompt-driving contract belongs only to the retired CAO interactive demo workflow.
**Migration**: Use the maintained Houmao-server interactive demo for supported multi-turn interactive walkthroughs.

### Requirement: Fixed local CAO target
**Reason**: The fixed-loopback CAO target was a pack-specific assumption of the retired demo.
**Migration**: Use the maintained Houmao-server demo's demo-owned server authority instead of the removed fixed-loopback CAO workflow.

### Requirement: Live inspection affordances
**Reason**: The live inspection surface is specific to the retired CAO interactive demo.
**Migration**: Use the maintained Houmao-server interactive demo's inspect and verification surfaces.

### Requirement: Explicit interactive teardown
**Reason**: This teardown contract only governed the retired interactive CAO demo pack.
**Migration**: Use the maintained Houmao-server interactive demo stop flow for supported teardown behavior.

### Requirement: Live control-input driving against an active session
**Reason**: The raw `send-keys` control-input contract is part of the retired CAO interactive demo workflow.
**Migration**: No direct replacement is introduced in this change. Supported interactive guidance moves to the Houmao-server demo pack, which does not expose the same raw control-input workflow in v1.

### Requirement: Control-input artifacts remain distinct from prompt-turn verification
**Reason**: This artifact rule only existed for the retired CAO interactive demo's split between prompt turns and raw control input.
**Migration**: No direct replacement is required because the maintained Houmao-server interactive demo does not preserve this raw control-input tutorial contract.
