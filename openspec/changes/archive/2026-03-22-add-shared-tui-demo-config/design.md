## Context

The shared tracked-TUI demo pack already has working workflows for recorded capture, replay comparison, review-video generation, and live watch. The problem is not missing capability so much as an unclear control surface: the current demo behavior is spread across scenario JSON files, CLI defaults, and Python constants, which makes it hard for developers to answer basic questions such as which knobs are supported, which knobs change tracker semantics, and which knobs only affect human-facing review artifacts.

This becomes more important now that the demo is being used for real fixture authoring and tracker evaluation. Sampling cadence is not merely a convenience knob. It changes the evidence stream that the standalone tracker sees, which means the demo needs a clear way to expose capture cadence, explain its relationship to review-video cadence, and let developers run robustness sweeps without confusing presentation settings with semantic settings.

The user-facing baseline for this change is deliberately pragmatic:

- default tmux sampling should match the Houmao server baseline of `0.2s`,
- generated review video should reflect the actual capture cadence by default rather than an unrelated fixed FPS, and
- developers should be able to see and vary those knobs from one checked-in config file owned by the demo itself.

## Goals / Non-Goals

**Goals:**
- Introduce one demo-owned `demo-config.toml` that makes the shared tracked-TUI demo’s supported knobs visible and explicit.
- Separate evidence-production knobs, tracker-semantic knobs, tool-launch knobs, and presentation knobs so developers can reason about what changing a value means.
- Align the default capture cadence with the existing Houmao server baseline by defaulting tmux sampling to `0.2s`.
- Make review-video cadence follow capture cadence by default so the review artifact honestly reflects the evidence cadence that produced the replay.
- Support capture-frequency robustness testing without pretending that one canonical per-sample ground-truth file can be reused unchanged across different sampling cadences.
- Persist resolved config into run artifacts so comparisons and reports explain which knobs were active.

**Non-Goals:**
- Changing the standalone tracker’s public-state contract or the GT-comparison contract.
- Introducing `houmao-server` into the demo workflow.
- Replacing scenario files; they can remain the place for per-case interaction scripts while config owns defaults and profiles.
- Guaranteeing that every state remains detectable at arbitrarily low capture frequencies.

## Decisions

### Decision: Add a checked-in demo-owned `demo-config.toml` as the authoritative configuration surface

The demo will gain a checked-in `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml` that serves as the default configuration surface for recorded validation, live watch, and sweep execution. Demo commands will load this config by default, then apply profile selection, scenario-specific overrides, and CLI overrides on top.

Why this approach:
- It gives developers one discoverable place to inspect supported knobs.
- It avoids continuing to treat Python constants and scenario JSON fields as the public configuration contract.
- A checked-in file makes the default behavior reviewable in code review and easier to document.

Alternatives considered:
- Keep using scenario files plus CLI flags as the effective config surface.
  Rejected because that hides which defaults are canonical for the demo as a whole.
- Put defaults into code and only document them in Markdown.
  Rejected because developers need something executable and inspectable, not only prose.

### Decision: Classify config into evidence, semantics, presentation, launch, paths, profiles, and sweeps

The config schema will distinguish at least these groups:

- `tools`: tool-specific launch defaults and recipe paths
- `paths`: fixture and output roots
- `evidence`: tmux sampling interval, runtime observation cadence, timeouts, capture mode
- `semantics`: tracker-facing timing knobs such as `settle_seconds`
- `presentation`: review-video resolution, codec, and frame retention
- `profiles`: named bundles of overrides
- `sweeps`: named matrices such as capture-frequency robustness runs

Why this approach:
- It makes the meaning of each knob explicit.
- It prevents developers from conflating evidence changes with public-state semantic changes.
- It creates a clean place to add future robustness or operator profiles without inventing new ad hoc CLI flags.

Alternatives considered:
- Use one flat config namespace.
  Rejected because it hides the distinction between “changes what the tracker observes” and “changes how artifacts are displayed.”

### Decision: Default capture cadence to `0.2s` and derive review-video cadence from capture cadence

The demo’s default `sample_interval_seconds` will be `0.2`, matching the existing Houmao server baseline and the terminal-recorder default. Review-video generation will default its effective FPS from capture cadence, so a run captured at `0.2s` produces review media at `5 fps` unless an operator explicitly overrides presentation settings.

Why this approach:
- It makes the demo immediately comparable to the server-side environment the team already uses.
- It removes the misleading split where prior review video claimed `8 fps` while the underlying evidence was captured more slowly.
- It keeps the review artifact honest about what evidence was and was not observable.

Alternatives considered:
- Keep capture at `0.25s` and review video at fixed `8 fps`.
  Rejected because it creates duplicated frames that look smoother than the underlying evidence stream really was.
- Raise canonical capture to `0.125s`.
  Rejected for this change because the immediate requirement is to match the existing Houmao server baseline first.

### Decision: Keep canonical GT comparison sample-aligned only for the chosen baseline profile, and use transition-contract validation for capture-frequency sweeps

The canonical recorded fixture workflow will continue to compare human-authored GT against replayed public tracked state on the baseline capture profile. Capture-frequency robustness sweeps will not reuse that GT as if it were cadence-invariant. Instead, sweep validation will compare higher-level transition contracts such as required transition families, terminal result expectations, forbidden terminal states, and timing drift tolerances.

Why this approach:
- Different capture cadences generate different evidence surfaces and timing quantization, so one per-sample GT timeline is not a sound oracle across all cadences.
- Developers still need a meaningful way to evaluate whether the tracker remains robust as capture cadence changes.
- Transition-contract validation preserves the semantic question being asked without forcing false precision.

Alternatives considered:
- Reuse the exact baseline GT timeline for every sampling frequency.
  Rejected because the resulting mismatches would often reflect sampling quantization rather than real tracker regressions.
- Require separate hand-authored GT for every sweep frequency.
  Rejected because it is too expensive for routine robustness testing.

### Decision: Persist resolved config into each run and report

Every run will emit the resolved demo configuration that actually governed the run after defaults, selected profile, scenario overrides, and CLI overrides are merged. Summary reports should reference that resolved config so developers can tell whether a result reflects evidence cadence, semantic timing, or presentation choices.

Why this approach:
- Without resolved-config evidence, sweep comparisons are hard to interpret later.
- It gives developers a durable audit trail when a fixture or robustness run is reviewed after the fact.

Alternatives considered:
- Only print resolved settings to stdout.
  Rejected because stdout is not a durable artifact for later reasoning or bug reports.

## Risks / Trade-offs

- [More visible knobs can encourage unsupported combinations] → Mitigation: document semantic classes clearly and keep a small set of named profiles for common usage.
- [Developers may confuse review-video FPS with capture cadence even after the change] → Mitigation: default presentation FPS from capture cadence and persist both values in run artifacts.
- [Sweep verdicts may feel less exact than sample-by-sample GT comparison] → Mitigation: keep strict GT comparison for the canonical baseline and use transition contracts only for robustness sweeps.
- [Scenario files and config file could drift] → Mitigation: make scenario files primarily case-specific interaction definitions while config owns global defaults and profiles.
- [Changing defaults to `0.2s` may affect artifact size and timing expectations] → Mitigation: make the resolved config explicit in manifests and allow profiles for slower local iteration.

## Migration Plan

1. Add the new demo-owned config spec and delta requirements for recorded validation and live watch.
2. Introduce `demo-config.toml` plus loader and resolution logic in the demo pack.
3. Move current scattered default values into the config surface, preserving CLI overrides.
4. Switch default capture cadence to `0.2s` and make review-video cadence derive from capture cadence by default.
5. Add profile and sweep support, including persisted resolved-config artifacts and summary reporting.
6. Update demo documentation so developers understand when to use strict GT comparison versus sweep contracts.

Rollback is straightforward: the demo can continue to function with the previous hard-coded defaults if the new config loader is reverted, and no long-lived external API needs migration.

## Open Questions

- Whether review-video cadence should ever be allowed to diverge from capture cadence in canonical fixture publication, or only for ad hoc operator debugging.
- Whether the first sweep matrix should include only capture frequency or also runtime-observer cadence once the config surface exists.
