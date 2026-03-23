## Context

The repository already has CAO demo packs, dummy-project fixtures, a runtime shadow parser stack, and the Rx-based shadow lifecycle monitor used by `cao_rest` in `shadow_only`. What it does not have is one self-contained manual-validation pack that launches both Claude Code and Codex through houmao, lets the operator interact with each live TUI directly, and shows continuously updating parser and lifecycle state for both sessions in parallel.

This change intentionally targets operator validation rather than automated result extraction. The goal is to make it easy to watch state transitions such as `idle -> working -> awaiting_operator -> idle`, observe projection changes, and confirm that the runtime's `shadow_only` semantics remain legible during real interactive use.

The user also wants this pack to be independent from the existing demo wrappers under `scripts/demo/` and `src/houmao/demo/`, to force `shadow_only`, to use a demo-owned dummy-project workdir, and to render the monitor with `rich` for better visibility.

## Goals / Non-Goals

**Goals:**
- Provide a standalone demo pack under `scripts/demo/` that does not shell out to other demo-pack scripts.
- Launch one Claude Code CAO session and one Codex CAO session through houmao in `shadow_only`.
- Provision a tracked projection-oriented dummy project fixture into demo-owned workdirs rather than using the repository checkout as the live agent workdir.
- Run a separate monitor process in its own tmux session that polls both terminals every 0.5 seconds and renders a `rich` dashboard for parser and lifecycle state.
- Persist raw monitor samples and transition events for post-run inspection.
- Keep the operator workflow simple: `start`, attach to the two agent sessions and the monitor, manually interact, then `stop`.

**Non-Goals:**
- Reusing or wrapping the existing interactive demo shell scripts.
- Creating a snapshot-based golden-output verifier for the live monitor UI.
- Replacing the runtime-owned `shadow_only` monitor inside `cao_rest`.
- Supporting `cao_only` or mixed parsing modes in this pack.
- Adding mailbox, gateway, or multi-agent messaging behavior to this demo.

## Decisions

### Standalone pack structure

The pack will live under `scripts/demo/cao-dual-shadow-watch/` and own its own shell entrypoint, Python driver, monitor script, README, and output layout.

Why:
- The existing interactive demo pack owns a single-workspace lifecycle and forcefully manages the fixed loopback CAO server for that one session.
- Reusing it twice would couple two sessions to behavior designed for a single session and risks replacement-side effects during startup.

Alternatives considered:
- Wrap `cao-interactive-full-pipeline-demo` twice.
  Rejected because it is not structurally independent and its startup path is optimized for replacing one active session, not maintaining two concurrent sessions.

### Shared CAO server, isolated per-agent workdirs

The pack will manage one shared loopback CAO server for the run while provisioning separate demo-owned workdirs for Claude and Codex under the run root.

Why:
- One shared CAO server keeps operator setup and cleanup simple.
- Separate workdirs avoid cross-tool edits, `.git` state conflicts, and confusing projection diffs while still keeping both agents on the same tiny fixture shape.

Alternatives considered:
- One shared workdir for both agents.
  Rejected because concurrent manual edits by both tools would contaminate the state-validation signal.
- Separate CAO servers per agent.
  Rejected because it increases lifecycle complexity without improving the state-watch goal.

### Dedicated dummy-project fixture posture

The pack will provision a projection-oriented dummy project fixture from `tests/fixtures/dummy-projects/` into run-local paths and initialize each copy as a fresh standalone git repository.

Why:
- The operator wants the demo to validate TUI state changes, not repository-scale exploration.
- A copied dummy project gives predictable surfaces, faster startup, and stable manual exercises.

Alternatives considered:
- Use the main repository checkout or a git worktree.
  Rejected because that would add unrelated repository complexity to a parser-state validation demo.

### `shadow_only` is mandatory

All session starts and any resumed control commands in this pack will force `--cao-parsing-mode shadow_only`.

Why:
- The purpose of the pack is to validate shadow parser and lifecycle detection behavior directly.
- Allowing `cao_only` would weaken the demo contract and make operator observations ambiguous.

Alternatives considered:
- Expose a generic parsing-mode flag.
  Rejected because the pack is not a general CAO tutorial; it exists specifically for `shadow_only` validation.

### Monitor uses core runtime modules, not other demo surfaces

The monitor will talk directly to CAO and the shadow parser stack:
- `CaoRestClient.get_terminal_output(mode="full")`
- `ShadowParserStack(tool=...)`
- shadow parser contracts from `shadow_parser_core.py`

It will not poll another demo pack's `inspect` command.

Why:
- The current inspect surfaces are too coarse for this use case and do not expose all parser axes or lifecycle derivation inputs.
- A standalone pack should depend on shared runtime modules, not sibling demo wrappers.

Alternatives considered:
- Repeatedly run another demo's `inspect --json`.
  Rejected because it is not independent and does not expose enough state.

### Demo-local lifecycle derivation mirrors runtime semantics

The monitor will maintain demo-local readiness and completion trackers that mirror the runtime `shadow_only` semantics:
- readiness states: `ready`, `waiting`, `blocked`, `failed`, `unknown`, `stalled`
- completion states: `inactive`, `in_progress`, `candidate_complete`, `completed`, `blocked`, `failed`, `unknown`, `stalled`

The completion tracker will arm from the last known ready baseline when a session leaves ready state and then shows post-submit activity. It will use the same default timing posture as runtime shadow monitoring unless the pack explicitly overrides it:
- `unknown_to_stalled_timeout_seconds = 30.0`
- `completion_stability_seconds = 1.0`

Why:
- The operator wants to validate state changes continuously, not only terminal outcomes.
- The exported Rx pipelines in `cao_rx_monitor.py` are optimized for terminal monitor results, while the demo dashboard needs the intermediate states to stay visible over time.

Alternatives considered:
- Reuse the Rx pipelines directly as the only source of truth.
  Rejected because they emit terminal outcomes rather than the full continuously visible dashboard state.
- Invent unrelated demo-only state labels.
  Rejected because the pack is supposed to validate runtime semantics, not replace them.

### `rich` dashboard plus machine-readable evidence

The monitor will render a live `rich` dashboard in a dedicated tmux session and also persist:
- `samples.ndjson` for every poll tick
- `transitions.ndjson` for state-change-only events

Why:
- `rich` makes two-agent concurrent state inspection much easier to scan than plain console logs.
- Persisted NDJSON makes the demo useful after the live session ends or when a maintainer wants to diff transitions manually.

Alternatives considered:
- Plain `print()` log stream only.
  Rejected because it is harder to scan and loses the at-a-glance comparison between agents.

## Risks / Trade-offs

- [Tool UI drift] -> Parser states may change as Claude Code or Codex update their TUI surfaces. Mitigation: show parser preset/version, availability, anomalies, and projection tails so the monitor remains diagnosable when classification changes.
- [Full-output polling cost] -> Polling `mode=full` every 0.5 seconds is heavier than terminal-status polling. Mitigation: the pack targets only two sessions, keeps the workdir tiny, and persists samples for tuning if the cadence needs adjustment.
- [Demo-local state derivation divergence] -> The dashboard's tracker could drift from runtime semantics if the runtime monitor evolves later. Mitigation: keep naming, timing defaults, and status rules aligned with `cao_rx_monitor.py`, and centralize the demo-local tracker logic in one small module.
- [Shared CAO server blast radius] -> One CAO failure affects both agents. Mitigation: fail fast, preserve monitor artifacts, and render disconnection/failure clearly instead of silently hiding it.
- [Fixture ambiguity] -> The requested “projection dummy project” is not yet a stable named repository contract. Mitigation: introduce or document a dedicated tracked dummy-project fixture for this demo instead of hard-coding an implicit repo workdir assumption.

## Migration Plan

This is an additive change:

1. Add the standalone demo pack and any supporting dummy-project fixture.
2. Document the operator workflow in the pack README.
3. Keep existing demo packs unchanged.

Rollback is straightforward: remove the new demo pack and its dedicated fixture if the workflow is not useful. No runtime data migration is required.

## Open Questions

- None currently blocking. The implementation should settle on the tracked projection-oriented dummy-project fixture path during the same change so the README and startup defaults stay concrete.
