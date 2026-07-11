# Houmao Development Testing Skill

Status: Design draft

## Purpose

Design the `houmao-dev-testing` development skill. The skill will guide a repository contributor through agent configuration, managed launches, headless checks, native TUI evidence capture, manual state labeling, deterministic replay, and capture-cadence robustness testing.

The skill belongs in `skillset/dev/`. It is for development of Houmao itself and must not be published as a Houmao runtime skill.

## Artifacts

- [Use Cases](usecases/README.md)
- [Interface Design](design/README.md)

## Current Stage

The initial use case and the interfaces that support it are designed. A feature requirement and the detailed agent-skill overview have not been created yet.

## Related Context

- `docs/getting-started/quickstart.md`: maintained project, specialist, profile, launch, prompt, state, and stop workflow.
- `docs/getting-started/easy-specialists.md`: supported provider and launch-posture matrix.
- `docs/reference/terminal-record/index.md`: recorder commands and artifact authority boundaries.
- `docs/reference/tui-tracking/replay.md`: shared tracker replay pipeline and public tracked-state model.
- `scripts/demo/shared-tui-tracking-demo-pack/README.md`: current recorded validation and cadence-sweep workflow.
- `scripts/demo/shared-tui-tracking-demo-pack/GT_STATE_COMPARISON_CONTRACT.md`: strict ground-truth and coarse cadence-sweep comparison rules.
- `src/houmao/shared_tui_tracking/`: maintained Claude, Codex, and Kimi tracker implementations.
- `extern/orphan/codex/` and `extern/orphan/kimi-code/`: local upstream source references for provider CLI behavior.

## Open Questions

- Should variable-cadence stream derivation become a terminal-recorder command or an extension of the shared TUI tracking demo pack?
- Which recorded fixtures may be committed after transcript redaction, and which must remain under ignored local output roots?
- Should the first skill version cover the full scenario taxonomy or start with ready, success, interruption, and TUI-down cases?
