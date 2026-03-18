## Context

The completed `rx-shadow-turn-monitor` change moved CAO `shadow_only` lifecycle logic from the old `_TurnMonitor` abstraction in `cao_rest.py` to the dedicated ReactiveX monitor module in `src/houmao/agents/realm_controller/backends/cao_rx_monitor.py`, while keeping current-thread polling ownership in `cao_rest.py`. The maintained docs did not move with that implementation change, so several developer and reference pages still describe the old module boundary, old completion rule, and old change-evidence surface.

This drift is cross-cutting rather than local to one page. The stale explanations are spread across the developer guide, operator-facing reference pages, troubleshooting guidance, and broader runtime reference material. The change therefore needs an explicit design so the resulting docs stay coherent and do not just patch isolated sentences while leaving the overall mental model inconsistent.

## Goals / Non-Goals

**Goals:**
- Restore a single consistent published explanation of the shipped TUI parsing contract after the Rx monitor rewrite.
- Make the parser/runtime boundary clear: provider parsers still classify one snapshot, while runtime lifecycle monitoring now lives in `cao_rx_monitor.py` and the CAO polling loops that feed it.
- Document the current completion and stall semantics, including `completion_stability_seconds`, normalized-text change evidence, mailbox observer bypass behavior, and recovery from stalled.
- Keep operator-facing pages concise while ensuring the deep explanation lives in the developer guide.
- Tie the maintained explanation to the current implementation and behavior-defining tests so later changes have obvious doc touchpoints.

**Non-Goals:**
- Changing runtime behavior, configs, or tests beyond what is needed to document them.
- Reopening the design decisions already settled in `rx-shadow-turn-monitor`.
- Performing a broad docs information architecture rewrite outside the TUI parsing area unless a small navigation update is required.

## Decisions

### D1: Model this as a new documentation capability, not a runtime behavior delta

**Choice:** Add a new `tui-parsing-docs` capability rather than modifying `brain-launch-runtime`.

**Rationale:** The runtime behavior change already landed and is already covered by the completed `rx-shadow-turn-monitor` change. This follow-up change defines the maintained documentation contract for that shipped behavior. Treating it as a docs capability makes the scope honest and keeps behavior requirements separate from documentation quality and coverage requirements.

**Alternative considered:** Modify `brain-launch-runtime` again just to record documentation updates. Rejected because it would blur the line between shipped runtime behavior and the repo's maintained explanation of that behavior.

### D2: Update the existing TUI parsing guide in place; add a new page only if clarity requires it

**Choice:** Rewrite the existing architecture, shared-contracts, runtime-lifecycle, maintenance, and provider pages in place, and add one focused developer page only if the Rx monitor explanation cannot fit cleanly into the current guide structure.

**Rationale:** The current guide already has the right conceptual homes: architecture for module boundaries, runtime-lifecycle for lifecycle semantics, shared-contracts for text-surface meanings, and maintenance for update rules. Adding a new page by default would create more navigation surface before proving the existing structure is insufficient.

**Alternative considered:** Always add a dedicated Rx monitor page. Rejected as the default because it risks splitting the lifecycle story across too many pages and leaving the old pages partially stale.

### D3: Keep one canonical deep explanation and make reference pages summarize it

**Choice:** The developer guide remains the canonical deep explanation, while `docs/reference/realm_controller.md`, `docs/reference/cao_claude_shadow_parsing.md`, and `docs/reference/cao_shadow_parser_troubleshooting.md` provide shorter operator-facing summaries and point back to the guide.

**Rationale:** The current drift happened partly because high-level reference pages and deep-dive pages evolved separately. A clearer canonical/dependent split reduces duplication pressure and makes future maintenance easier.

**Alternative considered:** Expand the reference pages until they are self-sufficient. Rejected because it would duplicate the design narrative across too many locations.

### D4: Document current lifecycle semantics from implementation and tests, not from superseded abstractions

**Choice:** The updated docs will treat these as the primary source surfaces:
- `src/houmao/agents/realm_controller/backends/cao_rx_monitor.py`
- `src/houmao/agents/realm_controller/backends/cao_rest.py`
- `src/houmao/agents/realm_controller/launch_plan.py`
- `tests/unit/agents/realm_controller/test_cao_rx_monitor.py`
- `openspec/changes/rx-shadow-turn-monitor/`

The docs will explicitly stop describing `_TurnMonitor` as the current runtime implementation and will stop describing `dialog_text` as the current lifecycle-evidence surface.

**Rationale:** The shipped semantics now live across code, tests, and the completed OpenSpec change. Using those surfaces directly avoids backsliding into the already-stale pre-Rx explanation.

**Alternative considered:** Preserve legacy wording and only add a short note about the new module. Rejected because that would leave the main mental model wrong.

### D5: Keep the docs focused on contract and operator meaning, not raw Rx operator internals

**Choice:** The updated docs will explain the runtime monitor in terms of readiness/completion phases, stability windows, recovery/reset behavior, source files, and test surfaces. They will mention relevant Rx concepts where helpful, but will not try to document every operator chain line-by-line.

**Rationale:** The goal is a maintained contract explanation, not an implementation transcript. Readers need to understand what the monitor does, where it lives, and how to safely change it, not memorize every `ops.switch_latest()` path.

**Alternative considered:** Mirror the full operator topology in the docs. Rejected because it would overfit the prose to one implementation shape and become brittle.

## Risks / Trade-offs

**[Documentation duplication]** → Multiple pages need updates, so the same concept could be restated inconsistently. Mitigation: keep the developer guide as the canonical deep explanation and make shorter pages summarize and link.

**[Overfitting docs to current implementation details]** → A too-literal Rx walkthrough would age quickly. Mitigation: document contract, source boundaries, and behavior-defining tests rather than every operator composition.

**[Optional new page adds navigation sprawl]** → Adding a page without need could fragment the reading path. Mitigation: add a new page only if the existing architecture/lifecycle pages remain unclear after rewrite, and update every relevant index if that happens.
