## 1. Demo Config Foundation

- [x] 1.1 Add a demo-owned `demo-config.toml` under `scripts/demo/shared-tui-tracking-demo-pack/` with sections for tools, paths, evidence, semantics, presentation, profiles, and sweeps.
- [x] 1.2 Add typed config models and loader/resolution logic under `src/houmao/demo/shared_tui_tracking_demo_pack/` that merge demo defaults, profile selection, scenario overrides, and CLI overrides deterministically.
- [x] 1.3 Persist the resolved demo configuration into run artifacts so later reports and debugging can see which settings governed each run.

## 2. Recorded Validation Integration

- [x] 2.1 Update recorded-capture and recorded-validation flows to resolve their default launch, output, evidence, semantic, and presentation settings from `demo-config.toml`.
- [x] 2.2 Change the default tmux sampling cadence to `0.2s` for recorded validation while preserving explicit override support.
- [x] 2.3 Update review-video generation so the default effective video cadence follows the underlying capture cadence instead of using a separate fixed FPS, while still allowing explicit presentation overrides.

## 3. Live Watch Integration

- [x] 3.1 Update live watch startup and runtime orchestration to resolve launch and observation defaults from `demo-config.toml`.
- [x] 3.2 Ensure live-watch outputs persist the resolved demo config together with the existing run artifacts and reports.

## 4. Robustness Sweeps

- [x] 4.1 Add config-defined capture-frequency sweep support that can execute the same scenario or fixture workflow at multiple sampling cadences.
- [x] 4.2 Implement transition-contract-based sweep evaluation so cadence variants are judged on required transitions, terminal outcomes, and timing tolerances rather than on a reused per-sample GT timeline.
- [x] 4.3 Emit sweep-friendly Markdown summaries and issue docs that explain which cadence variants passed, failed, or lost observability.

## 5. Documentation And Verification

- [x] 5.1 Update the demo-pack README and related developer-facing docs to explain the new config surface, the `0.2s` default baseline, and why review-video cadence now matches capture cadence by default.
- [x] 5.2 Document when strict GT comparison is valid versus when transition-contract sweep validation should be used for cadence robustness questions.
- [x] 5.3 Add or update tests that cover config resolution precedence, default cadence behavior, derived review-video cadence, and sweep-contract evaluation.
