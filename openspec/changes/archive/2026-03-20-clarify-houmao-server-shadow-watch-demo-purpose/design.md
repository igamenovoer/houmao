## Context

The current `houmao-server` dual shadow-watch pack already launches live Claude and Codex sessions through the supported `houmao-server + houmao-srv-ctrl` pair and polls `houmao-server` for current terminal state. The architectural shift has already happened: `houmao-server` now owns the authoritative parser-facing surface, lifecycle reduction, lifecycle authority, recent transitions, and visible-state stability metadata.

What remains inconsistent is the demo's framing and presentation. Parts of the README, interactive guide, profile text, and dashboard labels still read like the demo itself owns shadow-state semantics. That creates the wrong operator mental model and makes some labels actively misleading, especially where completion debounce is shown with wording that now overlaps with server-owned visible-state stability.

This change is cross-cutting but narrow:
- demo purpose and operator workflow copy
- monitor rendering semantics
- tests that encode the monitor contract
- spec language for the existing `houmao-server-dual-shadow-watch-demo` capability

## Goals / Non-Goals

**Goals:**
- Make the demo's purpose explicit: interactively prompt Claude/Codex and observe `houmao-server` tracked state as it changes.
- Keep `houmao-server` as the only authority for parser, lifecycle, transition, and stability semantics.
- Remove or rename demo-facing labels that imply demo-owned tracking logic.
- Extend the monitor contract so operators can see server-owned lifecycle authority and visible-state stability distinctly from completion debounce timing.
- Update docs and test guidance so maintainers understand the demo as a server-state observation surface.

**Non-Goals:**
- Changing `houmao-server` tracking semantics or payload shape.
- Reintroducing demo-local parser or lifecycle reducers.
- Replacing the current standalone pack structure or launch flow.
- Eliminating all server configuration knobs from the demo runner; some remain useful for reproducible startup.

## Decisions

### Decision 1: Treat the demo monitor as a thin server-state adapter

**Choice:** Keep the monitor as a polling/rendering layer over `HoumaoTerminalStateResponse` and explicitly avoid any demo-local tracking or reclassification.

**Rationale:**
- The server payload already contains the fields operators need.
- A second reducer would drift from the authoritative server contract and recreate the problem this change is meant to remove.
- The existing implementation is already structurally aligned with this model.

**Alternatives considered:**
- Add a demo-local smoothing or interpretation layer by default.
  Rejected because it would blur the boundary between authoritative tracked state and optional presentation policy.
- Reintroduce direct CAO polling for “more detail.”
  Rejected because the pack is specifically meant to show the server-owned tracked-state contract.

### Decision 2: Separate visible-state stability from completion debounce in the UI and docs

**Choice:** Dashboard text, README explanations, and interactive guide language will distinguish:
- visible-state stability from `state.stability`
- completion debounce timing from `lifecycle_timing.completion_stability_seconds`
- completion authority from `lifecycle_authority`

**Rationale:**
- The server contract now has separate concepts for “the visible state stopped changing” and “an anchored completion candidate stayed quiet long enough.”
- Conflating them leads operators to infer completion from quietness or vice versa.
- The current `stable=` label is no longer precise enough.

**Alternatives considered:**
- Keep current labels and rely on operator intuition.
  Rejected because the current labels encode the wrong mental model after the server contract revision.

### Decision 3: Keep runner timing fields, but treat them as server startup posture

**Choice:** The demo may continue to accept and persist timing knobs such as poll interval, completion stability, and unknown-to-stalled timeout, but docs, inspect output, and the dashboard header will treat them according to ownership:
- `poll_interval_seconds` is monitor-local cadence
- `completion_stability_seconds` and `unknown_to_stalled_timeout_seconds` are server posture configured for that run

**Rationale:**
- Those values are still useful for reproducibility and debugging.
- Removing them immediately is unnecessary churn.
- The problem is semantic ownership, not the existence of configuration.

**Implementation guidance:**
- The header should split monitor-local timing from server posture instead of showing one flat `stable=` line.
- Concrete wording may use labels such as `monitor: poll=...` and `server posture: completion_debounce=... unknown->stalled=...`.
- Per-agent visible stability should be shown from `state.stability`, not by overloading the completion debounce label.

**Alternatives considered:**
- Remove all timing-related inputs from the demo.
  Rejected because it would reduce observability and make reproducing tracked-state behavior harder.

### Decision 4: Rewrite operator-facing copy around prompt-and-observe workflow

**Choice:** README, autotest guide, and profile copy will describe the pack as:
- start the server-backed demo
- attach to the live TUIs
- submit short prompts or trigger interactive situations
- watch server-tracked fields change in the monitor

**Rationale:**
- This matches the actual user value of the pack.
- It avoids implying that the demo is the place where parser/lifecycle logic is implemented.
- The profile can still steer the agents toward short turns that make server state easy to observe without claiming any tracking responsibility.

**Alternatives considered:**
- Leave profile/guide wording mostly unchanged and update only the dashboard.
  Rejected because the stale framing appears in multiple operator entry points.

### Decision 5: Do not surface the configured visible-stability threshold in this change

**Choice:** For this change, current-state stability metadata is sufficient. The demo will not add explicit exposure of a configured visible-stability threshold until `houmao-server` exposes that threshold cleanly as part of its public contract.

**Rationale:**
- The current server payload already provides the operator-facing stability signal the demo needs.
- Surfacing a threshold the server CLI does not currently expose would create a partial or speculative contract.
- This keeps the change focused on clarifying ownership and presentation rather than expanding server configuration.

**Alternatives considered:**
- Add a demo-only threshold surface now.
  Rejected because it would outrun the current server contract and blur ownership again.

### Decision 6: Audit active references with an inventory and leave archived history alone

**Choice:** The artifact revision and later implementation pass should use a grep-based inventory of active references that still imply CAO-local ownership, update the active files, and leave archived change documents untouched as historical records.

**Rationale:**
- The repository has both live operator surfaces and archived design history.
- Active files need consistent current semantics; archived files should continue to describe the older model accurately.
- A lightweight inventory makes coverage auditable without adding much process overhead.

**Alternatives considered:**
- Best-effort sweep without an inventory.
  Rejected because it is harder to verify and easier to miss stale active references.

## Risks / Trade-offs

- [Presentation-only change may miss latent code drift] → Keep tests focused on the monitor as a server-state consumer so wording cleanup does not hide real contract regressions.
- [Operator confusion during transition] → Update README, guide, and dashboard labels together instead of changing only one surface.
- [Server payload may evolve again] → Phrase the demo contract around consuming server-owned state categories rather than pinning every cosmetic detail of the current dashboard layout.
- [Timing knobs remain visible] → Make their ownership explicit so they are read as startup configuration, not demo-local semantics.

## Migration Plan

1. Update the `houmao-server-dual-shadow-watch-demo` spec delta to reflect server-consumer semantics.
2. Revise monitor rendering and labels to expose server-owned authority/stability clearly.
3. Update README, interactive guide, and profile copy to match the new purpose.
4. Refresh unit tests for the server-backed monitor contract.

Rollback is straightforward: revert the demo copy and rendering changes. No server data migration is required because this change does not alter tracked-state storage or payloads.

## Open Questions

None currently blocking.
