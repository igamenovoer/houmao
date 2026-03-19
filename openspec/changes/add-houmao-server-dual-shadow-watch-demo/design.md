## Context

The current dual shadow-watch pack under `scripts/demo/cao-dual-shadow-watch/` launches a shared CAO server, starts Claude and Codex through the runtime `cao_rest` backend, then polls CAO output and re-runs the parser stack inside the demo monitor. That made sense before the server pair existed, but it now creates a split authority: `houmao-server` owns live tracking for the supported pair, while the demo still derives a second version of readiness, completion, projection change, and stalled behavior locally.

The public pair already provides the right ownership boundary:

- `houmao-server` is the public HTTP authority and owns direct tmux/process/parser tracking.
- `houmao-srv-ctrl launch` delegates the launch but registers the session into `houmao-server` and materializes `houmao_server_rest` runtime artifacts.

That means a new demo should validate the Houmao-owned path directly. The main design constraint is parity with the current demo surface: the existing dashboard exposes not just parser fields but also timing-sensitive lifecycle semantics such as `candidate_complete`, `unknown`, and `stalled`. The current server contract exposes operator state and general visible-signature stability, but it does not yet expose the full timing surface the current demo uses for display.

From a hack-through-testing perspective, the current change also lacks a canonical runnable journey. The intended real user path is interactive, not CI-style: a maintainer starts a demo-owned Houmao server, launches two real live sessions against copied dummy projects, attaches to the live TUIs, watches the server-owned monitor, interacts, inspects artifacts, and stops the run. The change should therefore make that path explicit, make prerequisite failures fast and observable, and define how future implemented `autotest/` assets will support both quick automatic blocker discovery and full interactive testing.

This change also overlaps conceptually with the in-progress `add-shadow-watch-state-stability-window` change. Implementation should treat that work as subordinate to the server-owned authority established here rather than letting the demo define another primary tracker.

## Goals / Non-Goals

**Goals:**
- Add a new standalone demo pack that teaches the supported `houmao-server + houmao-srv-ctrl` path instead of the raw CAO path.
- Make one canonical interactive operator workflow explicit enough to drive future hack-through-testing.
- Preserve the current operator workflow shape: copied dummy-project workdirs, two live agent TUIs, one monitor tmux session, machine-readable evidence, and a simple `start` / `inspect` / `stop` flow.
- Make `houmao-server` terminal state and transition history the authoritative monitor input.
- Preserve the old demo's manual-validation semantics, including explicit blocked/failed/unknown/stalled and completion progress states, by moving any missing timing logic into the server-owned contract.
- Keep the demo isolated from an operator's normal server state by using a demo-owned server instance and runtime root.
- Define fail-fast preflight checks, bounded timeout behavior, and deterministic output locations so patch-forward testing discovers the next real blocker quickly.
- Define the design-phase `testplans/` and intended implemented `autotest/` layout, with both automatic and interactive variants.

**Non-Goals:**
- Replacing the internal child CAO adapter in `houmao-server` or making the demo CAO-free internally in v1.
- Retrofitting the existing `cao-dual-shadow-watch` pack in place.
- Reintroducing a demo-local parser stack or demo-local lifecycle state machine as the authoritative source of truth.
- Expanding `houmao-srv-ctrl` into a native Houmao launch implementation in this change.

## Decisions

### Decision 1: Add a new Houmao-owned demo pack instead of mutating the CAO pack

**Choice:** Create a new pack under `scripts/demo/houmao-server-dual-shadow-watch/` with matching package modules under `src/houmao/demo/houmao_server_dual_shadow_watch/`.

**Rationale:** The old pack remains a useful reference for the CAO-era validation flow, while the new pack can state its authority model clearly from the start. This avoids muddling docs, tests, and assumptions around whether a given pack is validating raw CAO polling or Houmao-owned tracked state.

**Alternatives considered:**
- Rewrite `scripts/demo/cao-dual-shadow-watch/` in place.
  Rejected because it would keep a CAO-branded path for a Houmao-owned workflow and blur the boundary between the old and new demo contracts.

### Decision 2: The demo owns one dedicated `houmao-server` instance on a demo-specific loopback port

**Choice:** The pack starts one demo-owned `houmao-server serve` process with a demo-local runtime root and a demo-selected public base URL, then waits for `houmao-server` health before launching sessions.

**Rationale:** The current public default `http://127.0.0.1:9889` is already meaningful for normal operator flows. Reusing or replacing that listener would risk collisions with unrelated work. A demo-owned listener and runtime root keep the run isolated and make cleanup straightforward.

**Alternatives considered:**
- Reuse an already-running operator `houmao-server`.
  Rejected because demo state, registrations, and live sessions would be mixed with unrelated operator state.
- Keep managing raw `cao-server` directly and only point the monitor at `houmao-server`.
  Rejected because that would preserve split authority at startup time.

### Decision 3: The canonical HTT path is interactive, with one companion automatic preflight/lifecycle case

**Choice:** Treat the canonical user path as:

1. run demo preflight and start,
2. attach to Claude, Codex, and monitor tmux sessions,
3. interact with the live TUIs while watching server-owned state,
4. inspect evidence, and
5. stop the run cleanly.

Alongside that canonical interactive path, plan one smaller automatic case that only proves preflight, startup, inspect, and stop so the first environment or lifecycle blocker is discovered quickly without requiring live operator interaction.

**Rationale:** The feature is inherently about observing live interactive state, so the real user path must stay canonical. But interactive-only designs are slow to patch forward when basic prerequisites or lifecycle behavior are broken, so a smaller automatic companion path provides the fail-fast lane.

**Alternatives considered:**
- Make the automatic case the only canonical path.
  Rejected because that would reduce the change to a smokeable setup check and miss the real operator journey.
- Leave the change purely manual with no automatic companion path.
  Rejected because early blocker discovery would be too slow and too dependent on live operator attention.

### Decision 4: Session startup goes through `houmao-srv-ctrl launch` from each agent workdir

**Choice:** After fixture provisioning, the driver launches one Claude session and one Codex session through `houmao-srv-ctrl launch --headless --session-name ... --provider ... --agents projection-demo --port ...`, running each launch from the corresponding copied project directory.

**Rationale:** This uses the supported public CLI seam and naturally preserves the per-agent working-directory posture. It also ensures successful launches flow through `houmao-srv-ctrl` registration and `houmao_server_rest` artifact materialization instead of bypassing them through the older runtime startup path.

**Alternatives considered:**
- Continue using `start_runtime_session(..., backend=\"cao_rest\")`.
  Rejected because it bypasses the new public pair and keeps the demo tied to CAO-era runtime startup semantics.
- Teach the demo to launch through raw `houmao-server` session/terminal creation routes.
  Rejected because the user explicitly wants the CLI-pair workflow, and the launch-registration seam already exists in `houmao-srv-ctrl`.

### Decision 5: Preflight checks and lifecycle waits fail fast with bounded timeouts

**Choice:** The canonical runner surfaces must check prerequisites before launch and must never hang indefinitely during server start, delegated launch, inspect, or stop. At minimum, the implementation should preflight:

- `pixi`
- `tmux`
- `cao`
- `houmao-server` and `houmao-srv-ctrl` entrypoints
- provider-specific credentials/profile readiness
- the profile or agent-package surface needed for `--agents projection-demo`
- selected loopback port availability

Startup, delegated launch registration, monitor-readiness checks, and stop behavior should all use bounded waits with explicit timeout errors and preserved logs.

**Rationale:** HTT is about reaching the next real blocker quickly. Missing prerequisites and silent hangs are the two biggest wastes of time in demo-driven live testing.

**Alternatives considered:**
- Auto-install or auto-heal missing profiles during start.
  Rejected because it hides environmental assumptions and makes failures less diagnosable.
- Leave waits open-ended and rely on operator interruption.
  Rejected because it produces ambiguous failures and wastes time.

### Decision 6: The monitor consumes only `houmao-server` state/history surfaces

**Choice:** The monitor polls `HoumaoServerClient.terminal_state()` for current state and uses server-produced transitions as its transition evidence. It does not call `CaoRestClient`, capture CAO `mode=full` output, or run `ShadowParserStack` locally.

**Rationale:** The demo should validate the server-owned live tracker, not compete with it. Consuming the public server routes keeps the monitor a read-only visualization layer over the supported Houmao contract.

**Alternatives considered:**
- Shell out to `houmao-server terminals state` on every refresh.
  Rejected because repeated CLI process startup is slower and less direct than using the same public HTTP contract via `HoumaoServerClient`.
- Keep local CAO polling and only compare it to server output.
  Rejected because that recreates the split-authority problem and complicates operator interpretation.

### Decision 7: Add server-owned lifecycle timing metadata and stalled classification for demo parity

**Choice:** Extend the tracked-state payload from `houmao-server` with a dedicated lifecycle-timing block and server-owned stalled semantics. At minimum, the authoritative state should expose:

- readiness states: `ready`, `waiting`, `blocked`, `failed`, `unknown`, `stalled`
- completion states: `inactive`, `in_progress`, `candidate_complete`, `completed`, `blocked`, `failed`, `unknown`, `stalled`
- lifecycle timing metadata:
  - `readiness_unknown_elapsed_seconds`
  - `completion_unknown_elapsed_seconds`
  - `completion_candidate_elapsed_seconds`
  - `unknown_to_stalled_timeout_seconds`
  - `completion_stability_seconds`

**Rationale:** The existing `stability` block in `houmao-server` measures how long the visible signature has stayed unchanged. That is useful, but it is not the same thing as the current demo's unknown-to-stalled timer or completion-candidate timer. If the new demo is meant to preserve the same manual validation surface, those timers must move into the server-owned contract rather than being recomputed in the demo.

**Alternatives considered:**
- Treat general visible-signature stability as a replacement for the old completion and stalled timers.
  Rejected because it changes the meaning of the dashboard and loses parity with the current validation workflow.
- Recompute stalled and completion timing locally in the new demo.
  Rejected because it would create a second tracker semantics surface outside the server.

### Decision 8: Design-phase `testplans/` and implemented `autotest/` stay distinct

**Choice:** Keep design-phase HTT plans inside the change under:

- `openspec/changes/add-houmao-server-dual-shadow-watch-demo/testplans/case-preflight-start-stop.md`
- `openspec/changes/add-houmao-server-dual-shadow-watch-demo/testplans/case-interactive-shadow-validation.md`

Each plan covers both automatic and interactive variants and includes a Mermaid `sequenceDiagram`.

The intended implemented test assets live under the owned demo root:

- `scripts/demo/houmao-server-dual-shadow-watch/autotest/run_autotest.sh`
- `scripts/demo/houmao-server-dual-shadow-watch/autotest/case-preflight-start-stop.sh`
- `scripts/demo/houmao-server-dual-shadow-watch/autotest/case-preflight-start-stop.md`
- `scripts/demo/houmao-server-dual-shadow-watch/autotest/case-interactive-shadow-validation.sh`
- `scripts/demo/houmao-server-dual-shadow-watch/autotest/case-interactive-shadow-validation.md`
- `scripts/demo/houmao-server-dual-shadow-watch/autotest/helpers/common.sh`

Shell is the correct implementation language here because this repository's demo packs and autotest surfaces are already POSIX-shell-oriented.

**Rationale:** The OpenSpec change should capture the intended test design without pretending those are shipped implementation artifacts yet. The implemented demo-owned `autotest/` layout then becomes the durable execution surface.

**Alternatives considered:**
- Collapse the design plans and final autotest guides into one place.
  Rejected because it blurs design intent and implementation ownership.
- Hide case dispatch inside `run_demo.sh`.
  Rejected because HTT case selection should live in a dedicated harness, not an unrelated operator wrapper.

### Decision 9: Demo evidence mirrors server authority instead of re-diffing locally

**Choice:** `samples.ndjson` stores the server state snapshots the monitor actually consumed. `transitions.ndjson` records server-authored transitions or a thin wrapping of them with demo metadata; the monitor does not invent a second transition reducer.

**Rationale:** This keeps the persisted evidence honest. If an operator investigates a surprising state change, the saved artifacts should match what the server said, not what a second dashboard-specific reducer inferred.

**Alternatives considered:**
- Keep the current demo's local transition diff logic.
  Rejected because it would let the demo disagree with the server about what changed and when.

### Decision 10: Stop flow uses the server authority directly; CLI delete wrappers remain optional

**Choice:** The demo stop path can call the `houmao-server` HTTP authority through `HoumaoServerClient` for session teardown. Adding extra `houmao-server` CLI delete wrappers is optional follow-up ergonomics, not a blocker for this change.

**Rationale:** The public server authority already owns the live sessions. The demo does not need an additional CLI surface just to be correct.

**Alternatives considered:**
- Block the demo on new `houmao-server sessions delete` CLI commands first.
  Rejected because it widens the change without improving the core authority model.

### Decision 11: Artifact layout is deterministic and reviewable

**Choice:** The canonical runner and future `autotest/` cases should preserve deterministic or caller-selected output locations under the run root. At minimum, the run should keep:

- persisted demo state
- server stdout/stderr logs or redirected server-owned log paths
- monitor refresh logs
- `samples.ndjson`
- `transitions.ndjson`
- any preflight or autotest reports written by the implemented harness

**Rationale:** Interactive testing only becomes repeatable when failures leave enough evidence behind to diagnose them after the live session is over.

**Alternatives considered:**
- Treat the Rich dashboard as sufficient evidence.
  Rejected because it disappears when the session ends and cannot support later review.

## Risks / Trade-offs

- [Server contract expansion is larger than a pure demo change] -> Mitigation: keep the new fields additive on Houmao-owned extension routes and avoid changing CAO-compatible route semantics.
- [Projection-demo may not already be an installable `houmao-srv-ctrl` profile] -> Mitigation: add an explicit preflight/install step or document the prerequisite clearly before launch.
- [Interactive-only validation is slow to iterate when setup is broken] -> Mitigation: ship the automatic preflight/start-stop case early and keep it separate from the richer interactive guide.
- [Demo-owned server lifecycle adds another managed process] -> Mitigation: persist `started_by_demo`, pid/log metadata, and a run-local runtime root so `stop` can clean up deterministically.
- [The pair is still CAO-backed internally in v1] -> Mitigation: document clearly that the demo validates Houmao public ownership, not CAO removal from internal implementation.
- [Parallel in-progress demo work may conflict] -> Mitigation: treat this change as the authority-setting proposal and either absorb or supersede overlapping demo-only smoothing work before implementation starts.

## Migration Plan

1. Add the server-owned lifecycle timing/stalled contract needed for parity on `houmao-server` extension routes.
2. Add the new Houmao-owned demo pack plus its fail-fast preflight and bounded lifecycle behavior.
3. Port the monitor to `houmao-server` state/history consumption and preserve evidence output.
4. Add the implemented `autotest/` harness, automatic case, interactive guide, and shared helpers under the new demo root.
5. Document the new workflow and keep the old CAO demo pack unchanged during initial rollout.
6. If the new pack proves sufficient, decide later whether the CAO-branded demo should be deprecated or retained as a historical/reference path.

Rollback is additive and straightforward: remove the new pack and stop recommending it. The server-owned additive timing fields can remain if already adopted by other consumers.

## Open Questions

- Does `houmao-srv-ctrl install/launch` already support a lightweight `projection-demo` profile end to end, or does this change need to package that path explicitly?
- Should the demo expose only HTTP-client-driven teardown initially, or is there operator value in adding matching `houmao-server` CLI mutation helpers during the same change?
