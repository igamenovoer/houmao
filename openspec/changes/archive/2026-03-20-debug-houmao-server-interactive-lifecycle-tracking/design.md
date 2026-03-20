## Context

`houmao-server` already has a clear server-owned lifecycle hook for prompt submission: [`POST /terminals/{terminal_id}/input`] proxies the CAO-compatible input call and, on success, invokes `note_prompt_submission()` so the tracker can arm a turn anchor. The live interactive shadow-watch demo, however, is currently exercised by attaching to tmux and typing directly into the live Claude/Codex panes. The captured failure shows that visible prompt execution changes the parsed surface and stability metadata, but the server-tracked lifecycle never advances beyond `ready` / `inactive` / `unanchored_background`.

That leaves two realistic failure families:

1. the direct interactive path never reaches the server-owned prompt-submission hook, so the anchor is never armed, or
2. the tracker still misclassifies the observed parsed surface and reduction path even without an anchor.

We need an implementation path that produces hard evidence for both possibilities without relying on manual interpretation of live panes alone.

## Goals / Non-Goals

**Goals:**
- Add dense, structured, opt-in tracing around the server modules that participate in interactive lifecycle tracking.
- Make the tracing precise enough to answer whether prompt submission was recorded, whether an anchor was armed, which reduction branch was taken, and why transitions were or were not emitted.
- Provide an automatic repro workflow that runs the same demo substrate through both a server-owned input path and a direct tmux-input path.
- Persist all debug artifacts under a run-scoped repo-local `tmp/` directory so the investigation is repeatable and self-contained.

**Non-Goals:**
- Do not fix the lifecycle bug in this change.
- Do not turn the debug traces into a normal always-on server logging contract.
- Do not introduce a new public HTTP diagnostics API when filesystem artifacts are sufficient for the investigation workflow.
- Do not redefine the demo’s operator contract beyond what is needed to drive the debug repro automatically.

## Decisions

### 1. Use env-gated structured tracing, not ad hoc prints or always-on logs

The instrumentation will be enabled only when a dedicated debug environment flag is present. When disabled, normal `houmao-server` and demo runs remain unchanged and do not emit dense tracking traces.

When enabled, the server will append structured NDJSON events at key boundaries:

- app-layer input submission
- service-layer prompt-submission recording
- tracker anchor arming / loss / expiry
- tracker cycle ingestion
- parsed-surface to lifecycle-observation conversion
- reduction branch selection
- operator-state derivation
- stability-signature changes
- transition publication or suppression

Why this design:
- We need exact causal ordering across modules, not human-oriented freeform logs.
- NDJSON is easy to inspect, diff, grep, and summarize post-run.
- Opt-in gating keeps the instrumentation acceptable even if it is verbose.

Alternatives considered:
- Always-on `logging.warning(...)`: rejected because it is too noisy, timing-sensitive, and poorly structured for cross-module correlation.
- Only capture final `inspect` snapshots: rejected because it misses the critical internal branch decisions that explain why the final state is wrong.

### 2. Trace files should be run-scoped and grouped by concern

The debug workflow will write to a default repo-local root:

```text
tmp/houmao-server-tracking-debug/<timestamp>/
```

Within that root, artifacts will be grouped into:

- `events/` for NDJSON trace streams
- `artifacts/` for inspect snapshots, pane captures, and other point-in-time evidence
- `summary/` for a correlated human-readable run summary

Why this design:
- The investigation should be easy to rerun without manual cleanup.
- A run-scoped directory avoids interleaving unrelated traces.
- Grouping by concern keeps the output navigable even when the event volume is high.

Alternatives considered:
- Reuse the demo run root directly: rejected because the debug artifacts would mix with ordinary demo output and be harder to compare across runs.
- Emit one giant combined NDJSON file: rejected because per-concern streams are easier to inspect while still allowing correlation by shared keys.

### 3. Every trace event must carry correlation keys

Every emitted debug event should include enough metadata to correlate it with other streams without reconstructing context from source code. At minimum:

- `ts_utc`
- `monotonic_ts` when available
- `event_type`
- `terminal_id`
- `tracked_session_id`
- `tool`
- `cycle_seq` when the event belongs to a watch cycle
- `anchor_id` when the event belongs to anchored completion monitoring

Where payloads are large or sensitive, the instrumentation should prefer hashes, excerpts, and structured summaries over dumping unbounded blobs into every event.

Why this design:
- We need to prove whether the same terminal that received input is the tracker that armed or failed to arm an anchor.
- Cycle and anchor identifiers make absence meaningful: if no anchor-bearing events appear after a direct tmux prompt, that is itself evidence.

Alternatives considered:
- Infer correlation from filenames or timestamps alone: rejected because cross-module timing is too tight and too ambiguous for reliable postmortem interpretation.

### 4. The automatic repro must execute two explicit prompt paths

The debug runner will drive a fresh server-backed shadow-watch setup through two separate prompt-delivery modes:

1. a server-owned input path that uses the CAO-compatible `/terminals/{id}/input` route and therefore should invoke `note_prompt_submission()`
2. a direct tmux-input path that injects the prompt into the live pane without going through the server input route

The runner will capture the same classes of evidence for both paths:

- inspect snapshots before and after the prompt
- pane captures
- the trace streams
- a short final comparison summary

Why this design:
- The core unknown is path sensitivity. We need the same watched session model exercised through both prompt paths.
- If the server-owned path behaves correctly while direct tmux input does not, the missing-hook explanation becomes much stronger.
- If both paths fail the same way, the bug likely sits inside parser classification or reduction rather than input ownership.

Alternatives considered:
- Only reproduce the direct tmux path: rejected because it leaves no control path.
- Only reproduce through `/input`: rejected because it would not explain the observed interactive demo failure.

### 5. The runner should use the existing shadow-watch demo as the substrate

The automatic debug workflow should start the existing `houmao-server-dual-shadow-watch` demo rather than assembling an unrelated minimal environment.

Why this design:
- The failure was observed in that exact demo context.
- Reusing the demo preserves the real parser presets, terminal launch posture, monitor polling cadence, and session registration behavior.
- The resulting traces will be easier to compare with previously captured issue evidence.

Alternatives considered:
- Build a synthetic unit-style harness around `LiveSessionTracker` only: rejected because the issue may depend on real prompt transport and live parser observations.
- Launch ad hoc tool sessions outside the demo: rejected because it would change too many variables at once.

### 6. The debug runner may tune tracking cadence and timing posture per run

The debugging workflow may adjust timing-related parameters when that helps isolate the failure, including:

- state polling cadence
- visible-stability threshold
- completion debounce / stability timing
- unknown-to-stalled timeout

The effective values used for a run should be persisted in the debug artifacts and called out in the run summary so later comparisons stay honest.

Why this design:
- The failure may be masked or exaggerated by current cadence and debounce windows.
- Debugging needs the freedom to tighten or relax timing without pretending those temporary values are part of the normal operator contract.

Alternatives considered:
- Freeze all debug runs to production-like defaults: rejected because it would make the investigation unnecessarily rigid and could hide race conditions or branch timing.
- Let the runner vary timing without recording it: rejected because unrecorded timing changes would make the traces hard to trust.

### 7. Supplemental transport evidence may bypass the CAO-compatible path

The debug workflow may use workspace-available tools such as libtmux-backed pane inspection and terminal-recording helpers to capture additional transport evidence directly from tmux, even when those captures bypass the CAO-compatible server-control path.

Those supplemental captures are diagnostics only. They do not replace `houmao-server` as the tracked-state authority being investigated; they exist to explain what the live terminal was visibly doing when the server made a given tracking decision.

Why this design:
- The current failure may depend on differences between what the pane visibly displayed and what the server reduction pipeline concluded.
- Direct tmux and recording-based evidence gives a second view of the live terminal without requiring more guesswork.

Alternatives considered:
- Restrict all evidence collection to CAO-compatible APIs: rejected because the goal is to debug the server’s own tracking path, and CAO-compatible surfaces may hide transport details that matter.
- Replace server traces with libtmux-only diagnostics: rejected because that would dodge the actual server-side bug instead of explaining it.

## Risks / Trade-offs

- [Risk] Dense tracing may perturb timing-sensitive lifecycle behavior. → Mitigation: keep event writes append-only and lightweight, record both monotonic and wall-clock timestamps, and treat the server-owned input path as an internal control.
- [Risk] Debug artifacts may capture prompt or pane content that would be too sensitive for general use. → Mitigation: keep the workflow explicitly maintainer-only, disabled by default, and scoped to repo-local `tmp/` output; prefer hashes or excerpts in server event streams and keep full pane captures in explicit artifacts.
- [Risk] The direct tmux path may bypass the server so completely that some expected traces are absent. → Mitigation: the absence is itself part of the diagnosis; the summary should call that out explicitly rather than treating it as a logging failure.
- [Risk] Timing tweaks could accidentally be mistaken for the normal demo posture. → Mitigation: persist the effective timing values in every run summary and treat them as debug-run metadata, not as changes to the default operator contract.
- [Risk] Supplemental tmux or terminal-recording captures could be mistaken for the source of truth. → Mitigation: keep those artifacts explicitly labeled as supporting evidence while the server traces remain the primary subject of analysis.
- [Risk] Automatic comparison against live tools can be flaky if stale tmux sessions or old demo processes exist. → Mitigation: make the debug runner own a fresh run root, kill conflicting stale sessions/processes before launch, and preserve enough logs to explain setup failures.

## Migration Plan

This is an opt-in maintainer workflow, so there is no end-user migration.

Implementation should proceed in this order:

1. add the gated trace sink and event helpers
2. instrument the app/service/tracker boundaries
3. add the automatic debug runner and `tmp/` artifact layout
4. verify the runner produces a clean side-by-side control-vs-direct comparison

Rollback is straightforward: disable or remove the debug flag and runner without affecting the normal server or demo path.

## Open Questions

- Exact environment variable names for enabling tracing and selecting the output root can be finalized during implementation.
- The final runner surface can live under a demo-adjacent or debug-specific script path; the key design constraint is that it reuses the existing shadow-watch demo substrate and writes only under `tmp/`.
- The exact default timing overrides for a debug run can be chosen during implementation; the important contract is that the runner may tune them and must record what it used.
