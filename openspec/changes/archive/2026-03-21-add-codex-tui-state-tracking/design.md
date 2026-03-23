## Context

The repository already has a standalone shared Rx tracker core for screen-scraped TUI state reduction, but the current Codex integration leaks backend naming into that boundary. In particular, the tracker currently uses `codex_app_server` as a detector family label even though the problem we need to solve is interactive Codex TUI tracking from raw tmux-like snapshots, not headless Codex control.

Codex has multiple programmatic control modes with different contracts:

- interactive Codex TUI, which requires raw-snapshot parsing and send-keys style interaction,
- `codex app-server`, which is a structured headless protocol, and
- prompt-oriented CLI execution, which is another structured non-TUI contract.

Only the first mode belongs in the standalone tracked-TUI subsystem. The archived Codex `tui-signals` notes also show that Codex active/ready/success inference cannot rely on single-snapshot status-row matching alone. Some active states must be inferred across multiple recent snapshots because the visible busy row may disappear during streaming while the answer is still in flight.

The design therefore needs to preserve one shared Rx tracker engine while giving `codex_tui` enough profile-owned temporal logic to remain correct under externally controlled snapshot cadence.

## Goals / Non-Goals

**Goals:**
- Define `codex_tui` as a tracked-TUI app family distinct from Codex headless/backend names.
- Keep the standalone tracker scoped to interactive screen-scraped TUIs only.
- Preserve one shared Rx tracker session and shared turn-state vocabulary across Claude Code and Codex TUI.
- Allow a TUI profile to combine raw single-snapshot analysis with profile-owned temporal inference derived from a sliding time window.
- Capture Codex TUI signal semantics for activity, overlays, interruption, generic error blocking, steer handoff, and stable ready-return success.

**Non-Goals:**
- Track `codex_app_server` or prompt-oriented Codex CLI execution through the TUI tracker.
- Replace upstream headless contracts with screen-scraping heuristics.
- Introduce a separate public Codex-only state machine outside the shared tracker.
- Make snapshot cadence assumptions that depend on fixed sampling frequency.

## Decisions

### Decision: Model Codex under `codex_tui`, not backend labels

The standalone tracker app family for interactive Codex surfaces SHALL be named `codex_tui`.

Rationale:
- The shared tracker is about a visible interactive surface contract, not about how the process is launched or controlled elsewhere in the repo.
- `codex_app_server` is a backend/control-mode name and incorrectly suggests that the TUI tracker applies to the structured headless protocol.
- The clarified boundary is: screen-scraped interactive TUIs belong in `shared_tui_tracking`; structured headless Codex modes do not.

Alternatives considered:
- Keep `codex_app_server` as the tracker app id: rejected because it leaks backend naming into the wrong abstraction and conflates TUI scraping with headless protocol control.
- Use a generic `codex` tracker app id: rejected because the repo already uses `codex` as a broader tool selector covering multiple control modes with different contracts.

### Decision: Keep one shared Rx tracker engine and add a separate temporal-hint callback

The shared tracker session SHALL continue to own:
- event streams,
- settle timers,
- public tracked-state transitions,
- shared turn-state vocabulary, and
- injected-scheduler behavior.

Profile implementations SHALL be allowed to contribute:
- per-snapshot normalized facts,
- profile-private analyzed frames for recent-window inference, and
- temporal hints derived from recent ordered analyzed frames.

The shared engine SHALL own the session-local sliding recent-frame window, invoke the resolved profile's separate temporal-hint callback after each snapshot, merge the resulting temporal hints with the current per-snapshot `DetectedTurnSignals`, and then run the normal reduction logic.

`DetectedTurnSignals` SHALL remain the single-snapshot contract. Temporal inference SHALL use a separate hint type and explicit merge/gating step rather than silently changing the meaning of `detect()`.

For profiles that model success as a ready return after prior turn authority, the shared engine SHALL gate success candidacy on previously armed turn authority before settlement.

Rationale:
- Codex TUI needs cross-snapshot inference, but that does not justify a separate Codex-only public state machine.
- The existing shared Rx tracker already owns the right timing concerns; Codex needs richer profile logic, not a second architecture.
- A separate temporal-hint callback keeps single-snapshot facts traceable and prevents the current detector contract from becoming an implicit stateful API.

Alternatives considered:
- Put all temporal logic into the shared engine: rejected because Codex-specific growth/overlay semantics would spread tool rules into the core.
- Overload `detect()` or return a temporally modified `DetectedTurnSignals`: rejected because it would blur the single-snapshot contract and make diagnostics harder to interpret.
- Create a separate Codex-only reducer/session: rejected because it would fork the public contract and duplicate shared turn timing behavior.

### Decision: Use sliding time windows rather than pairwise-only snapshot inference

Profile-owned temporal inference for `codex_tui` SHALL use a sliding time window over recent frames rather than assuming that comparing only adjacent snapshots is sufficient.

Rationale:
- Snapshot cadence is external to the tracker and may be too sparse or too dense for pairwise heuristics to remain stable.
- Windowed inference lets the profile degrade confidence when recent evidence is too sparse instead of manufacturing certainty.
- The shared tracker already uses an injected scheduler, so time-window maintenance fits the existing Rx model naturally.

Alternatives considered:
- Pairwise comparison only: rejected because it makes correctness overly dependent on capture frequency.
- Count-based fixed window only: rejected because sample counts do not correspond reliably to elapsed time.

### Decision: Restrict single-snapshot Codex signals to current-surface facts

`codex_tui` single-snapshot analysis SHALL emit only current visible-surface facts such as:
- prompt/composer visibility,
- active status-row presence,
- in-flight tool-cell presence,
- blocking overlay presence,
- exact interruption presence,
- generic red error-cell presence,
- steer-handoff presence,
- ready-composer posture, and
- profile-owned surface or latest-turn region signatures.

Rationale:
- This keeps the single-snapshot layer testable and source-backed.
- It prevents the detector boundary from smuggling in hidden temporal assumptions.

Alternatives considered:
- Infer transcript-growth activity directly from a single snapshot: rejected because the archived Codex notes explicitly require multi-snapshot reasoning for that case.

### Decision: Codex TUI success is a stable ready return after prior turn authority

`codex_tui` success SHALL be modeled as a stable return to ready posture after prior armed turn authority, subject to blockers such as current overlays, exact interruption, or current latest-turn red error cells.

That prior turn authority MAY come from either:
- an explicit `on_input_submitted()` event, or
- prior stronger active-turn evidence that arms the shared tracker through surface inference.

The `Worked for ...` separator SHALL be treated as supporting evidence only, not as a mandatory success gate.

An initial idle ready-composer posture without prior armed turn authority SHALL NOT settle success.

Rationale:
- The archived Codex signal notes show that short or conversational Codex turns may omit a final `Worked for ...` marker.
- Requiring that marker would undercount valid successful turns.
- Snapshot-only replay/live flows remain viable only if surface-inferred turn authority can qualify when explicit input events are unavailable.

Alternatives considered:
- Require `Worked for ...` to settle success: rejected because it contradicts the source-derived signal notes.
- Require explicit input events for ready-return success: rejected because it would couple correctness to live-adapter behavior and would break snapshot-only replay/testing flows.
- Treat any ready composer as success: rejected because initial idle surfaces and post-error ready returns would be misclassified.

### Decision: Codex overlays degrade to unknown; generic red errors block success but are not known-failure alone

Codex approval modals, request-user-input modals, MCP elicitation, and app-link suggestion overlays SHALL degrade the public posture to `turn.phase=unknown` unless stronger active or terminal evidence exists.

Generic red `■ ...` error cells SHALL set current-error evidence and block success for the current turn, but SHALL NOT produce `known_failure` without a narrower Codex-specific rule.

Rationale:
- The archived signal notes are explicit that these surfaces are not stable enough for a dedicated public operator state or generic failure result.

Alternatives considered:
- Map overlays to a dedicated public ask-user state: rejected because the shared public contract intentionally avoids that tool-specific state explosion.
- Treat generic red error cells as known-failure: rejected because the same renderer is reused for heterogeneous situations, including exact interruption.

### Decision: Move app-specific tracker logic into app-owned modules and extract the current Codex detector as seed logic

The shared tracked-TUI package SHALL keep contracts, registry logic, surface helpers, and the Rx session engine in shared modules, while app-specific logic moves under app-owned modules such as `shared_tui_tracking/apps/codex_tui/`.

The existing `CodexTrackedTurnSignalDetector` SHALL be treated as migration seed logic to extract and decompose into `codex_tui` signal-family modules rather than duplicated under a second tracker identity.

The target structure for this change is:

```text
shared_tui_tracking/
  contracts.py
  session.py
  registry.py
  apps/
    codex_tui/
      __init__.py
      profile.py
      signals/
        activity.py
        overlays.py
        interrupted.py
        error_cells.py
        ready.py
```

Rationale:
- Codex temporal logic and signal families are large enough that keeping them inside the current flat detector file would continue the architecture leak this change is trying to fix.
- Extraction from the current Codex detector preserves existing source-backed logic while making ownership clear.

Alternatives considered:
- Keep Codex logic in the flat shared detector file and only rename the class: rejected because it preserves the current packaging shortcut and does not give Codex a clean app-owned boundary.
- Re-implement Codex logic from scratch in the new module tree: rejected because the current detector already contains useful single-snapshot logic that should be preserved and decomposed.

### Decision: Limit the naming migration to the tracker-facing boundary

This change SHALL rename tracker-facing app-family references from `codex_app_server` to `codex_tui` only where the standalone tracked-TUI subsystem resolves app identities.

Runtime/backend identifiers such as `BackendKind = "codex_app_server"`, backend modules, and runtime schemas SHALL remain unchanged unless a separate change explicitly targets them.

Rationale:
- The problem being solved is tracker-boundary leakage, not a repo-wide backend rename.
- Keeping runtime identifiers stable avoids accidental breakage in headless Codex paths that are out of scope for this change.

Alternatives considered:
- Rename every `codex_app_server` reference in the repo: rejected because it would overreach into headless/runtime layers this change does not own.
- Leave tracker-facing `codex_app_server` naming intact: rejected because it preserves the current architecture leak.

### Decision: Start with one `codex_tui` profile in v1 and keep latest-turn signatures profile-private

The first implementation SHALL ship one `codex_tui` profile for v1 rather than splitting renderer variants immediately.

Latest-turn-region signatures and any comparable profile-specific frame details SHALL remain profile-private in v1 rather than widening the shared normalized-signal contract.

Rationale:
- The current need is to establish the boundary and temporal mechanism, not to design a full renderer-variant matrix before divergence is proven.
- Keeping profile-specific signatures private avoids widening the shared signal model speculatively.

Alternatives considered:
- Split `codex_tui` into renderer variants immediately: rejected because the current change does not need that extra branching to deliver the agreed v1 contract.
- Add a shared latest-turn signature field now: rejected because only Codex currently needs it and the need can remain internal until a second tracker family proves it should be shared.

## Risks / Trade-offs

- [Codex TUI source drift] → Keep Codex logic inside `codex_tui` profile-owned modules so source changes are localized to one app family.
- [Window inference can be underconfident on sparse sampling] → Prefer degrading to `unknown` over manufacturing active/success certainty when the recent window is too sparse.
- [Naming migration from `codex_app_server` to `codex_tui` may touch docs and tests broadly] → Make the new app-family name explicit in specs and docs and update tracker-facing references together.
- [Profile-owned temporal logic can become too engine-like] → Keep the shared engine responsible for public state transitions and timers; keep profile-owned temporal logic limited to emitting normalized hints.

## Migration Plan

1. Introduce `codex_tui` as the tracked-TUI app family in the profile registry and tracker-facing docs/specs, while leaving runtime/backend names such as `codex_app_server` unchanged outside the tracker boundary.
2. Refactor the shared detector boundary into shared contracts/helpers plus app-owned modules, and extract the current `CodexTrackedTurnSignalDetector` into `shared_tui_tracking/apps/codex_tui/` seed logic.
3. Add a separate temporal-hint callback, a session-owned sliding recent-frame window, and an explicit engine merge/gating step while preserving the public Rx tracker session API.
4. Implement Codex TUI temporal inference and ready-return success semantics on top of that shared mechanism, with prior armed turn authority coming from either explicit input or surface inference.
5. Leave headless Codex paths outside the standalone tracker boundary; no runtime headless contract migration is required.
