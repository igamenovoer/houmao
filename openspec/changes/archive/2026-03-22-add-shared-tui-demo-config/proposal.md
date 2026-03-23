## Why

The shared tracked-TUI demo pack is already useful, but its operational knobs are fragmented across scenario files, CLI flags, and code defaults. That makes it hard for developers to see what is configurable, and it obscures an important testing question: whether tracker behavior remains robust when tmux capture cadence changes.

## What Changes

- Add a demo-owned `demo-config.toml` under `scripts/demo/shared-tui-tracking-demo-pack/` as the visible configuration surface for capture, tracker semantics, review-video generation, launch posture, and output layout.
- Align the demo’s default tmux capture cadence with the existing Houmao server baseline by setting the default sampling interval to `0.2s`.
- Change review-video defaults so the generated `.mp4` uses the same effective frame cadence as the underlying capture instead of a separate fixed video FPS.
- Add named config profiles and capture-frequency sweep definitions so developers can run the same demo workflow at multiple tmux sampling rates and inspect whether required tracker transitions remain observable.
- Persist resolved demo-config values into run artifacts so recorded validation and live watch outputs explain which evidence, semantic, and presentation knobs were in effect.

## Capabilities

### New Capabilities
- `shared-tui-tracking-demo-configuration`: Demo-owned configuration contract for the shared tracked-TUI demo pack, including defaults, profiles, and capture-frequency sweep definitions.

### Modified Capabilities
- `shared-tui-tracking-recorded-validation`: Recorded validation must load demo-owned defaults, default capture to `0.2s`, and derive review-video cadence from capture cadence unless explicitly overridden.
- `shared-tui-tracking-live-watch`: Live watch must use the same demo-owned configuration surface for launch, observation, and output defaults so the live workflow and recorded workflow stay aligned.

## Impact

- Affected code and docs: `scripts/demo/shared-tui-tracking-demo-pack/`, `src/houmao/demo/shared_tui_tracking_demo_pack/`, and developer-facing demo documentation.
- Affected workflows: recorded capture, recorded validation, live watch, and future robustness sweeps will resolve defaults from one checked-in config file rather than from scattered constants.
- Affected artifacts: run manifests and reports will include resolved configuration details so developers can reason about whether observed behavior reflects capture evidence, tracker semantics, or presentation choices.
