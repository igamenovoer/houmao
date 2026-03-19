## Context

The shadow parser classifies TUI state from tmux scrollback snapshots. Today, `_build_surface_assessment()` in both `claude_code_shadow.py` and `codex_shadow.py` extracts the last 100 lines of scrollback, runs regex detectors across the entire tail to produce boolean flags (`has_idle_prompt`, `has_processing`, `has_response_marker`, `operator_blocked_excerpt`, etc.), then feeds those flags to a priority-ordered if/elif chain in `_classify_surface_axes()`.

This "bag-of-signals" approach has no concept of which line is the current prompt vs. which lines are historical output. When the scrollback window contains both old signals (a response marker from a previous turn, an old slash command) and current signals (a fresh idle prompt), the priority chain can select the wrong signal because it has no temporal ordering within the window.

The Rx pipelines in `cao_rx_monitor.py` consume `SurfaceAssessment` as an opaque input — they don't know or care how it was derived. The fix is entirely internal to the per-provider parsers.

## Goals / Non-Goals

**Goals:**
- Eliminate misclassification caused by historical signals in the tail window
- Introduce a `prompt_boundary_index` that partitions each snapshot into a historical zone and an active zone
- Factor signal extraction into a pure function producing a typed `SnapshotSignalSet`
- Make state classification operate only on active-zone signals
- Fix `_active_prompt_payload()` fragility as a side effect of prompt-anchored detection
- Apply the fix to both Claude and Codex parsers
- Maintain the existing `SurfaceAssessment` external contract unchanged

**Non-Goals:**
- Changing the Rx temporal pipelines (`cao_rx_monitor.py`) — they consume the same `SurfaceAssessment`
- Adding prompt-to-answer association — that remains a separate layer per existing specs
- Changing dialog projection logic — the projector still operates on full scrollback
- Changing the tail window size (100 lines) — the window stays the same, but classification is zone-restricted
- Handling issue-004 (fresh-environment TUI noise) — that is a separate concern, though this fix reduces its blast radius

## Decisions

### D1: Prompt boundary is the start of the latest active interaction block

**Decision**: Scan the tail lines in reverse order, but interpret the result as the start of the latest active interaction block rather than blindly taking the bottommost spinner/progress line. Provider-defined boundary anchors include idle prompts, processing/progress surfaces, approval/menu surfaces, and setup/login surfaces. When a visible prompt owns spinner/progress lines below it, the `prompt_boundary_index` resolves to that prompt line so the active zone includes both the typeable prompt and the working evidence. Everything at or below the resolved boundary is the active zone. Everything above is historical.

**Rationale**: The bottom of the scrollback is still the most current part of the surface, but the repository already treats `working` and `input_mode` as coexisting axes. Defining the boundary as the true start of the active interaction block preserves the existing `working + freeform` contract and keeps `prompt_boundary_index` diagnostically meaningful.

**Alternative considered**: Treating the spinner/progress line itself as the boundary and then separately searching upward to recover a prompt. Rejected because it creates two competing "starts" of the active surface and makes the stored boundary less truthful.

### D2: Typed `SnapshotSignalSet` as a frozen dataclass

**Decision**: Introduce a `SnapshotSignalSet` frozen dataclass in `shadow_parser_core.py` that carries:
- `prompt_boundary_index: int | None` — line index within the tail where the active zone begins
- `active_zone_lines: tuple[str, ...]` — the lines from prompt boundary to tail end
- `historical_zone_lines: tuple[str, ...]` — the lines above the prompt boundary
- Provider-neutral common booleans scoped to the active zone: `has_idle_prompt`, `has_processing_spinner`, `has_response_marker`, `has_operator_blocked`, `has_slash_command`, `has_error_banner`
- `operator_blocked_excerpt: str | None` — extracted from active zone only
- `active_prompt_payload: str | None` — text after the prompt character on the anchor line
- `anchor_type: str | None` — which boundary anchor kind matched (`idle_prompt`, `spinner`, `selection_menu`, provider-specific setup/login kinds, or None)
- `blocked_surface_kind: str | None` — a generic provider-neutral hook for provider-specific blocked-surface semantics

**Rationale**: A typed value object makes signal extraction testable in isolation, documents the shared signal surface, and cleanly separates extraction from decision logic while keeping `shadow_parser_core.py` provider-agnostic.

**Alternative considered**: Returning a plain dict or NamedTuple. Rejected because frozen dataclass gives type checking, immutability, and clear field documentation.

### D3: Provider-specific `_extract_signals()` replaces inline flag computation

**Decision**: Each provider parser gets a new `_extract_signals(tail_lines, preset) -> SnapshotSignalSet` static method that replaces the inline boolean flag computation currently embedded in `_build_surface_assessment()`. The method:
1. Resolves the `prompt_boundary_index` as the start of the latest active interaction block
2. Partitions lines into zones
3. Runs signal detectors only against active-zone lines
4. Returns a `SnapshotSignalSet`

`_build_surface_assessment()` then calls `_extract_signals()` and passes the result to `_classify_surface_axes()`.

**Rationale**: Pure function, easy to test with synthetic tail lines. Provider-specific because anchor patterns differ between Claude and Codex (Claude uses `❯`, Codex uses `codex>`).

### D4: `_classify_surface_axes()` takes `SnapshotSignalSet` instead of boolean tuple

**Decision**: Refactor `_classify_surface_axes()` to accept a `SnapshotSignalSet` and derive axes from it. The priority chain logic is the same, but it now operates on signals that were extracted from the active zone only, so historical pollution is impossible.

**Rationale**: Minimal logic change — the if/elif chain works correctly when its inputs are clean. The bug was in the inputs, not the classification logic.

### D5: Shared zone-partitioning utility in `shadow_parser_core.py`, provider-owned anchor semantics in provider parsers

**Decision**: The generic reverse-scan utility lives in `shadow_parser_core.py` as `find_prompt_boundary(tail_lines, anchor_patterns) -> int | None`, but provider parsers remain responsible for defining richer boundary-anchor semantics and any provider-owned blocked-surface kinds. Claude and Codex may supply compiled patterns, predicate helpers, or other provider-owned matching inputs around the shared utility so the final `prompt_boundary_index` still points at the real start of the active interaction block.

**Rationale**: The reverse scan itself is shared, but the meaning of approval/login/setup/menu surfaces and the nuances of progress ownership are provider-specific. This keeps the shared core generic while still avoiding duplicate boundary-finding scaffolding.

### D6: No change to `DialogProjection` zone scoping

**Decision**: Dialog projection continues to operate on the full scrollback, not just the active zone. Only surface assessment classification is zone-restricted.

**Rationale**: The projector's job is to produce a best-effort dialog transcript for human or downstream consumption. It legitimately includes historical content. The issue is specifically about state classification — not about what text to show.

### D7: `output_variant` detection remains out of scope

**Decision**: `_detect_output_variant()` remains unchanged in this change. Zone-aware signal extraction only changes surface-state classification inputs, not output-family detection.

**Rationale**: The artifacts for this change define no new variant-detection behavior or verification. Keeping `output_variant` unchanged avoids coupling serialized parser metadata changes to this classification fix.

## Risks / Trade-offs

**[Risk: Anchor misfire on response text]** A response line that happens to start with `❯` or `codex>` could be mistakenly identified as the prompt boundary, splitting the active zone incorrectly.
→ Mitigation: The existing idle-prompt patterns are already tuned to avoid common false positives (e.g., `❯` only at line start with optional whitespace). Provider-owned boundary semantics can also prefer the owning prompt over raw spinner/progress lines, which keeps the boundary tied to the actual active block instead of a single bottommost regex hit.

**[Risk: No anchor found in tail]** If no anchor pattern matches in the 100-line tail (e.g., the tool is mid-output with no visible prompt/spinner/menu), `prompt_boundary_index` is None and the entire tail is treated as the active zone.
→ Mitigation: This falls back to today's bag-of-signals behavior, which is correct for this case — if there's no prompt visible, the tool is likely working and the whole tail is "current." `_detect_output_variant()` remains unchanged and continues to handle its existing unsupported/no-recognizable-signal cases independently.

**[Risk: Test maintenance burden]** Existing unit tests for classification assume bag-of-signals behavior and may need updating.
→ Mitigation: Tests that supply synthetic tail lines with signals at various positions need to be updated to reflect zone-aware behavior. This is a one-time cost and improves test quality by making the position-sensitivity explicit.

**[Trade-off: Two-pass scanning]** Signal extraction now does a backwards scan for the boundary first, then a forward pass for pattern matching within the active zone. This is slightly more work than the current single-pass scan.
→ Acceptable: The tail is at most 100 lines. Two passes over 100 lines is negligible.
