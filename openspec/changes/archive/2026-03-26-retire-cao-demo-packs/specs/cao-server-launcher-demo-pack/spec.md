## REMOVED Requirements

### Requirement: Repository SHALL provide a CAO launcher tutorial-pack demo under `scripts/demo/`
**Reason**: The standalone CAO launcher workflow is already retired, so keeping a live tutorial-pack contract for `scripts/demo/cao-server-launcher/` would preserve a demo for an unsupported operator surface.
**Migration**: Use the retirement guidance in `docs/reference/cao_server_launcher.md` and the supported `houmao-server + houmao-mgr` workflows instead of the removed standalone launcher demo pack.

### Requirement: Demo runner SHALL follow tutorial-pack execution mechanics
**Reason**: The runner behavior only existed to execute the retired standalone launcher tutorial pack.
**Migration**: No direct launcher-pack replacement is provided. Use maintained Houmao demo packs or pair workflow documentation for supported walkthroughs.

### Requirement: Demo runner SHALL execute launcher `status`, `start`, and `stop` with structured outputs
**Reason**: The standalone launcher entrypoint is retired and no longer supports the end-to-end lifecycle contract that this demo pack exercised.
**Migration**: Use `houmao-mgr server start|status|stop` and maintained Houmao-server demos for supported lifecycle walkthroughs.

### Requirement: Expected report updates SHALL be sanitized and reproducible
**Reason**: Expected-report maintenance for the launcher demo is no longer useful once the demo pack itself is retired.
**Migration**: No migration is required. Maintainers should stop updating launcher-demo snapshots because the demo pack is removed.

### Requirement: Demo README SHALL provide a complete step-by-step usage tutorial
**Reason**: The repository will no longer ship `scripts/demo/cao-server-launcher/` as an active tutorial surface.
**Migration**: Use active pair documentation and maintained demo packs instead of the removed standalone launcher tutorial README.
