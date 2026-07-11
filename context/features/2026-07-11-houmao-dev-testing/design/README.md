# Design

This directory contains interface and contract design notes for `houmao-dev-testing`.

## Index

| Design Doc | Purpose | Status |
| --- | --- | --- |
| [Public Interfaces](public-interfaces.md) | Define the skill interaction, test matrix, evidence layout, replay schedule, and verdict contracts | Draft |

## Module Map

- Skill interaction boundary: turns a developer request into a preflighted test session and pauses at human-review gates.
- Houmao managed-agent boundary: uses supported project, specialist, profile, launch, prompt, state, and cleanup commands.
- Native TUI evidence boundary: observes an ordinary provider process without injecting Houmao knowledge.
- Terminal recorder boundary: captures visual evidence and authoritative pane snapshots at the requested source cadence.
- Label boundary: stores operator-authored public-state expectations independently from tracker output.
- Replay boundary: feeds source or derived observations through the shared TUI tracker.
- Evaluation boundary: applies strict canonical comparison or semantic degraded-cadence contracts and emits explainable verdicts.

## Open Questions

- Where should the schedule-driven stream derivation implementation live?
- Should test-session manifests use YAML for authoring and JSON for resolved output, or use one format throughout?
- Which semantic coherence invariants should be global, and which should remain provider-profile-specific?
