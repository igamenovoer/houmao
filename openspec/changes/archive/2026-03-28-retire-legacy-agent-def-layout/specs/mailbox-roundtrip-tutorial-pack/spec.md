## REMOVED Requirements

### Requirement: Tutorial-pack runner SHALL follow self-contained execution mechanics
**Reason**: The current `scripts/demo/mailbox-roundtrip-tutorial-pack/` workflow is being archived under `scripts/demo/legacy/` and is no longer a maintained tutorial-pack obligation.
**Migration**: Retain any shared live mailbox/runtime fixtures separately. Specify redesigned tutorial automation later as new supported capabilities rather than preserving this archived tutorial-pack contract.

### Requirement: Tutorial-pack runner SHALL start two mailbox-enabled sessions on one shared mailbox root
**Reason**: This runtime contract belongs only to the current archived tutorial pack.
**Migration**: Any future maintained mailbox walkthrough should define its own startup and evidence contract after redesign instead of inheriting the archived workflow.
