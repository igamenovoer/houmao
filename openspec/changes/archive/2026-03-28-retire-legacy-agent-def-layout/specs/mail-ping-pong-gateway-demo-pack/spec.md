## REMOVED Requirements

### Requirement: Demo startup SHALL reuse the tracked mailbox-demo fixture family and launch one managed headless Claude participant plus one managed headless Codex participant through demo-owned `houmao-server`
**Reason**: The current `scripts/demo/mail-ping-pong-gateway-demo-pack/` workflow is being archived under `scripts/demo/legacy/` and no longer belongs in the maintained product contract.
**Migration**: Keep shared mailbox/demo fixtures in the live fixture tree where they remain useful, but redesign any future maintained gateway demo as a new capability instead of preserving this archived workflow.
