# Review: fix-cao-claude-output-mode-last — Shadow Provider Design Review

**Reviewer:** Claude (explore mode)
**Date:** 2026-02-28
**Scope:** Review the current (shadow provider) design for internal consistency, completeness,
and implementation readiness. The previous review (`review-20260228-issue-and-design-verification.md`)
is retained as historical context for the earlier design; this review covers the redesigned approach.

---

## 1. Design Summary (for clarity)

The current design departs from the original patch-CAO approach. The selected architecture:

```
  BEFORE (original plan)             AFTER (current design)
  ══════════════════════             ══════════════════════════

  Fix CAO's claude_code.py:          Runtime owns everything:
  - update RESPONSE_PATTERN     ──▶  - fetch mode=full from CAO (transport)
  - fix PROCESSING_PATTERN           - parse locally via shadow provider
  - fix extract_last_message()       - version-preset registry for patterns
                                     - shadow status from bounded tail
                                     - baseline cursor per turn
                                     - never return raw tmux output
```

Five design decisions anchor the approach:

| Decision | Summary |
|----------|---------|
| D1 | Shadow provider: CAO is transport only |
| D2 | Version-preset registry with floor lookup + env override |
| D3 | Output-driven shadow status with per-session baseline/cursor |
| D4 | Never return raw tmux output as the answer |
| D5 | Prevent accidental reliance on CAO status endpoints |

---

## 2. Cross-Artifact Consistency Check

### 2.1 Design ↔ Spec Coherence

Overall coherence is **good**. The spec requirements map cleanly to the design decisions,
and the scenarios cover the motivating failure modes. One vocabulary discrepancy stands out.

#### [GAP-1] `completed` shadow state used in design but not defined in spec (Medium)

Design Decision 3 says:

> "poll until `shadow_status == completed` (or `waiting_user_answer`) for that turn"

The spec (Requirement: Shadow status classification) defines only three shadow states:
- `processing` — spinner line present
- `waiting_user_answer` — selection UI present
- `idle` — idle prompt present, no higher-priority state

There is no `completed` state defined anywhere in the spec.

The implied semantics are: `completed` = the terminal is `idle` AND a response marker
appeared after the turn's baseline cursor. But that compound condition isn't expressed
as a named state in the spec — `idle` just means "idle prompt is visible."

This creates an implementation ambiguity: should the shadow status API expose a
`completed` state, or should the caller infer completion from (`idle` + baseline check)?

```
  TWO POSSIBLE INTERPRETATIONS
  ════════════════════════════

  Option A: completed is a first-class shadow state
  ─────────────────────────────────────────────────
  classify_shadow_status(lines, baseline) →
    processing | waiting_user_answer | completed | idle

  "completed" requires:
    - idle prompt present (no spinner), AND
    - a response marker appears after baseline offset

  Option B: completed is derived by the caller
  ─────────────────────────────────────────────
  classify_shadow_status(lines) →
    processing | waiting_user_answer | idle

  The polling loop in cao_rest.py checks:
    if status == idle and has_response_marker_after(baseline):
        → done

  Option A is cleaner and more testable: the logic lives
  in one place, tests can cover it directly, and callers
  don't need to re-implement the compound check.
```

**Recommendation:** Define `completed` as a first-class shadow state in the spec
(either by adding it to the classification requirement, or by adding a new requirement
that names the compound condition). Option A is preferred.

---

#### 2.2 Design ↔ Tasks Coverage

Tasks map well to design decisions. No obvious coverage gaps.

| Design Decision | Tasks |
|----------------|-------|
| D1 (shadow provider) | 1.1, 2.1, 2.2, 2.3 |
| D2 (version presets) | 1.2, 3.1 |
| D3 (shadow status + baseline) | 1.3, 1.4, 3.3 |
| D4 (no raw output) | 2.2, 3.2 |
| D5 (prevent CAO status reliance) | 2.1, 2.3 |
| Tests | 3.1, 3.2, 3.3 |
| Validation | 4.1, 4.2 |

---

## 3. Design Decision Review

### 3.1 D1 — Shadow Provider: GOOD

Treating CAO as a transport and owning parsing in the runtime is the correct call given
the constraints ("no modify CAO" + known CAO regex drift). The approach is well-bounded:
two CAO endpoints used (`mode=full` for scrollback, `POST /input` for sending), all
logic above them owned by this repo.

No issues.

---

### 3.2 D2 — Version-Preset Registry: GOOD, with one clarity note

The version-preset registry approach (floor lookup, env override, banner detection)
is well-designed. The fallback priority:

```
  1. AGENTSYS_CAO_CLAUDE_CODE_VERSION env var   (explicit pin)
  2. Auto-detected version from scrollback banner (dynamic)
  3. Latest known preset                          (fallback)
```

**One clarity note:** "latest known preset" is used when banner detection fails
(no version detected). For versions *older* than the oldest preset entry, floor lookup
correctly returns the baseline entry. But for the undetected-version case — when no
banner appears at all — the system falls back to the latest preset, which may have
patterns (e.g., `●` marker) that don't match an older Claude Code build.

This is not a blocking issue: the env override handles it operationally. But the
design and spec don't acknowledge this asymmetry. Worth a sentence noting: "if
version detection fails entirely, the latest preset is used; set
`AGENTSYS_CAO_CLAUDE_CODE_VERSION` to override if the latest patterns are wrong."

---

### 3.3 D3 — Shadow Status + Baseline/Cursor: DESIGN GAP (Medium)

This is the most implementation-rich decision, and it has one unresolved structural gap.

#### [GAP-2] Baseline/cursor mechanism is not specified (Medium)

Both the design and spec say "capture a baseline cursor at prompt submission time"
and use it to require that response markers appear *after* prompt submission. Neither
document specifies what form the baseline takes.

This matters because several valid forms have different tradeoffs:

```
  BASELINE FORM OPTIONS
  ═════════════════════

  A) Line count offset
     baseline = len(mode_full_output.splitlines())
     after-baseline lines = lines[baseline:]

     Pro: simple, easy to test
     Con: line count shifts if CAO returns different amounts of history

  B) Character/byte offset
     baseline = len(mode_full_output)
     after-baseline text = output[baseline:]

     Pro: exact boundary
     Con: fragile if scrollback trims or wraps differently

  C) Content marker (last N chars of output at submission time)
     baseline = output[-200:]   # or hash of last line
     Scan for this content in subsequent output to find the split

     Pro: survives scrollback normalization
     Con: complex, subtle failure modes

  Option A (line count) is the most straightforward and sufficient for
  the stated use case. The bounded tail window (Decision 3) further limits
  the search space, making minor offset drift acceptable.
```

Without specifying the baseline form, task 1.4 ("per-session baseline/cursor
handling") will be implemented ad-hoc. This makes the behavior hard to reason about
and hard to unit test.

**Recommendation:** Add a sentence to the design (or spec) specifying what a baseline
is — e.g., "the baseline is the line-count of the `mode=full` response at the time of
prompt submission; extraction and completion detection operate only on lines beyond
this offset."

---

#### [GAP-3] Tail window size is unspecified (Low)

Design and spec both use "for example the last N lines" without defining N. This is
explicitly flagged as an open question ("What is the smallest reliable tail window?"),
but it's not noted as blocking implementation.

In practice, a concrete default is needed for task 1.3 to be implemented consistently
and tested. The tail window affects both false-positive risk (stale scrollback) and
false-negative risk (too small to capture a long response).

This doesn't block the design direction, but should be resolved before task 1.3 is
started. A reasonable starting point (e.g., 100 lines for status checks, full content
after baseline for extraction) would allow implementation to proceed with a concrete
default that can be tuned.

---

### 3.4 D4 — Never Return Raw Output: GOOD

Clear, well-stated, testable. The spec requirement matches. Task 2.2 covers the
implementation.

One note: the design says "return a clear extraction failure with a short ANSI-stripped
tail excerpt for debugging." The spec says "surface a clear extraction failure." These
are consistent but the "tail excerpt" detail is only in the design — the spec doesn't
require it. That's fine (implementation detail), just noting it for completeness.

---

### 3.5 D5 — Prevent Accidental CAO Status Reliance: GOOD

Making the Claude Code path explicit (bypass generic wait loops) is good defensive
design. Task 2.1 covers this. No issues.

---

## 4. Open Questions Assessment

### OQ-1: Smallest reliable tail window (Low priority to resolve)

Design Open Question 1. Not blocking architecture. Should be resolved before task 1.3,
not necessarily before design is finalized. Suggest: define a concrete default and
document it as tunable.

### OQ-2: How to surface `waiting_user_answer` (Medium priority to resolve)

Design Open Question 2. This *does* affect the API design in task 2.1 and the behavior
visible to callers of the runtime. The options:

```
  WAITING_USER_ANSWER SURFACE OPTIONS
  ════════════════════════════════════

  A) Raise an exception (CallerActionRequired or similar)
     - Clean for the runtime caller
     - Requires the caller to catch and handle

  B) Return as structured response field (status=waiting_user_answer, answer=None)
     - Visible to higher-level callers
     - More inspectable
     - Requires a structured response type that doesn't exist yet

  C) Timeout and return the partial tail with a warning
     - Simple but lossy
     - Degrades gracefully for callers that don't handle B

  For brain-launch-runtime use cases, Option A is probably cleanest if the
  brain launch caller already handles errors. Option B is better if the runtime
  is expected to propagate state through layers.
```

This should be resolved before starting task 2.1 to avoid an ad-hoc decision in
the middle of implementation.

---

## 5. Spec Requirement Review

### 5.1 Requirement: Claude Code CAO output parsed by runtime shadow provider

Clear and well-scoped. The `processing`/`idle` scenario directly maps to the key
failure mode (spinner-only premature idle). ✓

### 5.2 Requirement: Preset resolved by version

Well-specified: priority order, floor lookup, env override, exact-match-first. ✓

### 5.3 Requirement: Shadow status classification is bounded

The bounded-tail requirement and the stale-scrollback scenario are clearly stated.
Gap: no `completed` state (see GAP-1). The scenario only tests the negative case
(don't misclassify stale output); the positive case (classify a finished turn as
completed) needs a counterpart scenario.

### 5.4 Requirement: Answer extraction is preset-scoped, ANSI-stripped, prompt-bounded

Solid. Covers the three extraction stop boundaries: idle prompt (ANSI-stripped), separator,
and baseline cursor. The ANSI-stripped matching for idle prompts (originally gap G1 in
the prior review) is explicitly required here. ✓

### 5.5 Requirement: Never return raw tmux scrollback

Clear and testable. ✓

---

## 6. Summary of Gaps

| # | Gap | Severity | Location | Recommendation |
|---|-----|----------|----------|----------------|
| GAP-1 | `completed` shadow state used in design, not defined in spec | Medium | design.md D3 / spec.md Req 3 | Define `completed` as first-class state in spec (idle + post-baseline response marker); add a positive-case scenario |
| GAP-2 | Baseline/cursor form is unspecified | Medium | design.md D3, spec.md Req 4, tasks 1.4 | Define baseline as line-count offset; add one sentence to design or spec |
| GAP-3 | Tail window size is unspecified | Low | design.md D3 / Open Q1 | Define a concrete default before task 1.3; resolve Open Q1 |
| GAP-4 | `waiting_user_answer` surface behavior left open | Medium | design.md Open Q2 | Resolve before task 2.1; recommend option A (exception) or B (structured field) |
| GAP-5 | "Latest preset" fallback for undetected version not acknowledged | Low | design.md D2 | Add a note that env override should be used if latest patterns are wrong for an older version |

---

## 7. Overall Assessment

### Is the design sound?

**Yes.** The shadow provider architecture is the right call. It is:
- Bounded in scope (two CAO endpoints, all logic runtime-owned)
- Testable without live tmux (mock `mode=full` responses)
- Operationally controllable (env override for version pinning)
- Honest about its heuristic nature (versioned presets, not "magic regexes")

The version-preset registry is well-designed and elegant: floor lookup, explicit
version entries, env override, no union-regex fragility. The core decisions (D1–D5)
are internally consistent and coherent with the spec.

### Is it ready to implement?

**Almost.** Two medium-severity gaps (GAP-1, GAP-2, GAP-4) should be resolved before
starting tasks 1.4 and 2.1 respectively. They are small — a sentence or scenario each —
but leaving them open invites ad-hoc choices during implementation that will be harder
to test and reason about.

The low-severity gaps (GAP-3, GAP-5) can be addressed during task execution without
blocking start.

### Recommended actions before starting implementation

1. **Resolve GAP-1**: Add `completed` to the spec's shadow status classification as a
   named state with explicit semantics (`idle` + post-baseline response marker). Add a
   positive-case scenario ("WHEN terminal is idle AND a response marker appears after
   baseline, THEN shadow status is completed").

2. **Resolve GAP-2**: Add one sentence to design.md D3 or spec.md Req 4 specifying the
   baseline representation (e.g., line-count offset into `mode=full` response at prompt
   submission time).

3. **Resolve GAP-4 (OQ-2)**: Pick a `waiting_user_answer` surface behavior and record
   the decision before task 2.1. Add it to design.md Decisions or as a note in tasks.md.

4. **Resolve GAP-3 (OQ-1)**: Pick a concrete default tail window size (e.g., 100 lines
   for status checks) before task 1.3. Update the spec or tasks with the default value.
