## Why

Kimi Code now has source-backed shared TUI signal tracking, but the maintained shared TUI tracking demo pack can only launch, watch, capture, and replay Claude or Codex sessions. We need a lightweight manual inspection path for Kimi before completing full `local_interactive` runtime integration.

## What Changes

- Extend `scripts/demo/shared-tui-tracking-demo-pack/` so live watch and recorded capture admit `tool = kimi`.
- Add Kimi demo-local launch assets, config entries, schema support, and test coverage to the restored shared TUI tracking demo pack.
- Add Kimi host-local auth-bundle projection guidance so operators can use an existing logged-in Kimi Code home without committing secrets.
- Add Kimi process/version detection and scenario control behavior, including Escape interruption and `kimi-code` / `kimi` process recognition.
- Add first-wave Kimi scenarios for manual state inspection: explicit success, interrupt after active, approval rejection, footer-thinking-ready, and TUI-down diagnostics.
- Extend recorded validation and sweep/corpus support so Kimi fixtures and fixture paths are first-class when authored later.
- Keep this scoped to the standalone shared TUI tracking demo pack; full managed-agent `local_interactive` Kimi launch remains in `add-kimi-tui-support`.

## Capabilities

### New Capabilities

### Modified Capabilities

- `shared-tui-tracking-demo-pack`: Add Kimi as a supported demo tool with secret-free launch assets, host-local auth alias materialization, and Kimi-specific process/version metadata.
- `shared-tui-tracking-demo-configuration`: Add Kimi tool configuration, schema fields, and documented defaults to the demo-owned config contract.
- `shared-tui-tracking-live-watch`: Allow live watch to start and inspect Kimi Code sessions through the standalone shared tracker dashboard.
- `shared-tui-tracking-recorded-validation`: Allow Kimi recorded capture, replay validation, scenario control, and sweep/corpus workflows.

## Impact

- Affected code:
  - `src/houmao/demo/shared_tui_tracking_demo_pack/`
  - `scripts/demo/shared-tui-tracking-demo-pack/`
  - `tests/unit/demo/shared_tui_tracking_demo_pack/`
- Affected assets:
  - Kimi demo-local `inputs/agents/tools/kimi/` and `interactive-watch-kimi-default.yaml`
  - Kimi scenario JSON files under the shared TUI tracking demo pack
  - demo config and packaged JSON Schema
- Affected workflows:
  - `run_demo.sh start --tool kimi`
  - `recorded-capture` with Kimi scenarios
  - `recorded-validate --tool kimi` and future Kimi fixture corpus validation
