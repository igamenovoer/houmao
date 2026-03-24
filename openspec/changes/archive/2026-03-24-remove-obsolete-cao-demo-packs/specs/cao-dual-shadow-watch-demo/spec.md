## REMOVED Requirements

### Requirement: Repository SHALL provide a standalone dual shadow-watch demo pack under `scripts/demo/`
**Reason**: The repository is retiring `scripts/demo/cao-dual-shadow-watch/` as an active maintained demo surface.
**Migration**: Use `scripts/demo/houmao-server-dual-shadow-watch/` and the active `houmao-server-dual-shadow-watch-demo` capability for maintained side-by-side monitoring workflows.

### Requirement: Demo startup SHALL provision demo-owned projection dummy-project workdirs
**Reason**: This startup contract exists only for the retired CAO dual shadow-watch demo pack.
**Migration**: The maintained Houmao-server dual shadow-watch demo continues to define its own dummy-project workdir posture in `houmao-server-dual-shadow-watch-demo`.

### Requirement: Demo startup SHALL launch one Claude session, one Codex session, and one monitor session in `shadow_only`
**Reason**: The repository is removing the CAO-managed dual-watch startup flow that launched these sessions through the old CAO path.
**Migration**: Use the maintained `houmao-server + houmao-srv-ctrl` launch flow defined by `houmao-server-dual-shadow-watch-demo`.

### Requirement: Monitor SHALL poll both live terminals every 0.5 seconds and render a `rich` dashboard
**Reason**: The retired CAO dual-watch monitor is being removed together with its demo-local polling and rendering flow.
**Migration**: Use the maintained monitor contract in `houmao-server-dual-shadow-watch-demo`, which consumes server-owned tracked state instead of the retired CAO-local monitor path.

### Requirement: Monitor SHALL expose parser and lifecycle fields needed for `shadow_only` validation
**Reason**: These display obligations are specific to the retired CAO dual-watch monitor.
**Migration**: Use the maintained field vocabulary and display contract defined by `houmao-server-dual-shadow-watch-demo`.

### Requirement: Monitor SHALL derive readiness and completion states from shadow-only lifecycle semantics
**Reason**: The repository is removing the old demo-local lifecycle derivation path together with the retired CAO dual-watch demo.
**Migration**: Use the maintained Houmao-server tracking surfaces instead of relying on the retired demo-local state derivation behavior.

### Requirement: Demo SHALL persist monitor evidence and stop cleanly
**Reason**: This persistence and teardown contract belongs only to the retired CAO dual-watch demo pack.
**Migration**: Use the persisted evidence and stop-flow contracts defined by `houmao-server-dual-shadow-watch-demo`.

### Requirement: README SHALL teach the manual state-validation workflow
**Reason**: The README contract is tied to a demo pack that will no longer exist as an active surface.
**Migration**: Follow the maintained operator workflow documented by `scripts/demo/houmao-server-dual-shadow-watch/` and specified by `houmao-server-dual-shadow-watch-demo`.
