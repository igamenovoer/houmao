# Review: fix-cao-claude-output-mode-last — Issue & Design Verification

**Reviewer:** Claude (explore mode)
**Date:** 2026-02-28
**Scope:** Verify that the found issue is real; evaluate whether the proposed design is sound.

**Update:** The change design has since been revised to avoid modifying upstream CAO source code. The selected approach is now a runtime-side “shadow provider” that parses `mode=full` and treats CAO `status`/`mode=last` as untrusted for Claude Code. The issue verification sections remain valid; the design proposal sections below are retained for historical context.

---

## 1. Issue Verification

### 1.1 Response Marker Mismatch — CONFIRMED

**Claim:** CAO hardcodes `⏺` (U+23FA) but Claude Code v2.1.62 uses `●` (U+25CF).

**Evidence:**

- `claude_code.py:28` — `RESPONSE_PATTERN = r"⏺(?:\x1b\[[0-9;]*m)*\s+"`
  Only matches `⏺`. No mention of `●` anywhere in the file.

- `claude_code.py:211` — error message confirms:
  `"No Claude Code response found - no ⏺ pattern detected"`

- `cao-server.log:13` —
  `GET /terminals/ff14e4db/output?mode=last HTTP/1.1" 404 Not Found`

- Issue doc (`context/issues/known/...`) reports observing `● OK` in `mode=full` output
  after prompting "Reply with exactly: OK" — response exists with `●` marker but
  `mode=last` cannot find it.

**Verdict: REAL.** The regex is hardcoded to a single Unicode codepoint that Claude Code
no longer uses.

---

### 1.2 Processing Detection Misses Spinner-Only Lines — CONFIRMED

**Claim:** `PROCESSING_PATTERN` requires a parenthesized suffix `\(.*\)` and misses
spinner lines like `✽ Razzmatazzing…`.

**Evidence:**

- `claude_code.py:33` — `PROCESSING_PATTERN = r"[✶✢✽✻·✳].*….*\(.*\)"`
  The trailing `\(.*\)` is mandatory.

- Demo `report.json` response_text (ANSI-stripped) shows:
  ```
  ❯ Reply with a single short sentence about test coverage.
  ✽ Razzmatazzing…
  ────────
  ❯
  ```
  The spinner line has no parenthesized suffix. `PROCESSING_PATTERN` would NOT match.

- `get_status()` (line 180-181) checks processing first. Since the pattern doesn't match,
  it falls through to IDLE (line 195-196) because it sees the `❯` prompt. Result: the
  terminal is classified as idle while Claude is still working.

- This causes the runtime to request output prematurely — before any response marker
  exists — which is the primary reason the demo shows spinner/prompt output instead of
  an answer.

**Verdict: REAL.** This is arguably the most impactful of the bugs, because it causes
premature output capture. Even a perfect marker fix won't help if the status is wrong.

---

### 1.3 Extraction Stop Condition Only Recognizes `>` Prompt — CONFIRMED

**Claim:** `extract_last_message_from_script()` stops on `>` but not on `❯`.

**Evidence:**

- `claude_code.py:226` — `if re.match(r">\s", line) or "────────" in line:`
  Only `>` is matched. No `❯`, no NBSP variant.

- Meanwhile, `IDLE_PROMPT_PATTERN` (line 34) correctly includes both: `r"[>❯][\s\xa0]"`.
  So `get_status()` recognizes `❯` as idle, but `extract_last_message_from_script()` does
  not stop extraction at `❯`.

**Verdict: REAL.** Inconsistency between status detection and extraction logic.

---

### 1.4 Runtime Fallback Chain Includes Unsupported `mode=tail` — CONFIRMED

**Claim:** Runtime falls back through `mode=tail` (HTTP 422) before `mode=full`.

**Evidence:**

- `cao_rest.py:248` — fallback loop: `for mode in ("tail", "full"):`

- `terminal_service.py:45-50` — `OutputMode` only defines `FULL` and `LAST`. No `TAIL`.
  Requesting `tail` triggers a 422 Unprocessable Entity.

- `cao-server.log` confirms the exact sequence:
  ```
  mode=last  → 404 Not Found
  mode=tail  → 422 Unprocessable Entity
  mode=full  → 200 OK
  ```

**Verdict: REAL.** The `tail` fallback is dead code that adds a wasted HTTP round-trip on
every failed extraction.

---

## 2. Design Evaluation

### 2.1 Decision 1 — Accept Both Markers: GOOD

Updating `RESPONSE_PATTERN` to accept both `⏺` and `●` is the correct fix.
Backward-compatible, minimal change, directly addresses root cause.

**No issues.**

### 2.2 Decision 2 — Resilient Processing Detection: GOOD, with a caveat

Making `\(.*\)` optional is the right fix for the immediate problem.

**Caveat:** The relaxed pattern `[✶✢✽✻·✳].*…` would match any line starting with a
spinner character followed by an ellipsis. While false positives are unlikely in normal
assistant output, the design should specify that the match should be applied to recent
output only (e.g., tail lines), not the full scrollback history. Currently `get_status()`
can be called with `tail_lines=None`, which searches the entire scrollback buffer. A
spinner from a previous turn could cause a COMPLETED terminal to be misclassified as
PROCESSING.

This is a pre-existing concern (the current strict pattern has the same theoretical
issue), but relaxing the pattern increases the surface area. The design should note this
and recommend that callers always pass a reasonable `tail_lines` value.

### 2.3 Decision 3 — Stop on `❯` Prompts: GOOD, but has an unaddressed bug

The decision to stop extraction on `❯` prompts is correct and fixes the inconsistency.

**Unaddressed bug in `extract_last_message_from_script()`:**

The current stop condition (line 226) uses `re.match(r">\s", line)` which operates on
**raw** (non-ANSI-stripped) lines. If the `>` or `❯` prompt is preceded by ANSI escape
codes (which it typically is in tmux output captured with `-e`), `re.match` anchors at
line start and will **not** match.

Example raw line from the demo:
```
\x1b[38;2;153;153;153m❯\xa0\x1b[7m\x1b[39m \x1b[0m
```

`re.match(r"[>❯][\s\xa0]", line)` would fail because the line starts with `\x1b[...`.

The design should specify that the stop condition should match against ANSI-stripped
lines (same as how `get_status()` strips ANSI before pattern matching). Otherwise, the
extraction may over-capture past the prompt boundary. This is currently masked by the
separator line check (`"────────" in line`), which uses `in` and works regardless of
ANSI position, but it's fragile — the separator is not always present between a response
and the next prompt.

### 2.4 Decision 4 — Runtime Fallback Hardening: GOOD

Defense-in-depth. Removing dead `mode=tail` fallback, stripping ANSI on `mode=full`
fallback, and refusing to return raw tmux output as the "answer" are all sound decisions.

---

## 3. Additional Findings

### 3.1 `get_status()` COMPLETED detection has a compound failure mode

`claude_code.py:191`:
```python
if re.search(RESPONSE_PATTERN, clean_output) and re.search(IDLE_PROMPT_PATTERN, clean_output):
    return TerminalStatus.COMPLETED
```

Since `RESPONSE_PATTERN` only matches `⏺`, a terminal where Claude finished with `●`
and shows a `❯` prompt would NOT be classified as COMPLETED. Instead it falls through
to IDLE (line 195-196).

This means `_wait_for_ready_status()` in the runtime might return when status is IDLE
after a response, which is technically fine (IDLE is in `_READY_STATUSES`), but it means
the semantic difference between "just booted up" and "finished answering" is lost. The
design mentions this in task 1.4 ("Ensure `get_status()` COMPLETED detection works with
updated markers") but doesn't call it out explicitly as a bug in the design document's
Decisions section. Worth making explicit.

### 3.2 Demo evidence doesn't directly prove marker mismatch in isolation

The demo output (`report.json`) shows output captured **during** processing (spinner +
prompt, no answer). This primarily demonstrates bug 1.2 (processing detection), not bug
1.1 (marker mismatch). The marker mismatch is documented in the issue file as a separate
observation with a different prompt ("Reply with exactly: OK" → `● OK`).

This doesn't invalidate anything — both bugs are independently verified from the source
code. But someone reading just the demo artifacts won't see direct evidence of the `●`
marker unless they also check the issue document.

### 3.3 The `get_status()` tail_lines behavior deserves a note

When `get_status()` is called without `tail_lines`, it searches the full scrollback.
The priority order is:

```
  PROCESSING → WAITING_USER_ANSWER → COMPLETED → IDLE → ERROR
```

If any previous turn left a spinner line or response marker in the scrollback, it could
affect status classification for the current turn. The design doesn't address this and
probably shouldn't (it's out of scope), but it's worth noting as a latent issue.

---

## 4. Conclusions

### Is the issue real?

**Yes, fully confirmed.** All four claimed sub-issues are verified from the source code,
and three are independently corroborated by demo artifacts and server logs. The primary
user-visible symptom (getting raw ANSI/spinner output instead of Claude's answer) is
a direct consequence of these bugs working in combination.

### Is the design good?

**Yes, with minor gaps.** The four design decisions are sound and well-reasoned. The
scope is appropriate (fix the vendored provider + harden the runtime, don't redesign
the architecture). The risks and trade-offs are honestly assessed.

**Gaps to address before implementation:**

| # | Gap | Severity | Recommendation |
|---|-----|----------|----------------|
| G1 | Extraction stop condition operates on raw ANSI lines; `re.match` will fail when prompt is ANSI-prefixed | Medium | Strip ANSI before matching stop conditions in `extract_last_message_from_script()`, consistent with `get_status()` |
| G2 | COMPLETED status detection in `get_status()` has same marker mismatch; not explicitly called out as a decision | Low | Add to Decision 1 scope or note in tasks — task 1.4 covers it implicitly but design should be explicit |
| G3 | Relaxed processing pattern + full-history search could increase false-positive risk | Low | Recommend that design note the `tail_lines` best practice; not a blocker |

### Overall assessment

The change is well-scoped, the issue is clearly real and well-documented, and the design
addresses the right problems with appropriate solutions. The gaps above are
implementation-level details that can be addressed during task execution without
changing the design's direction. **Recommend proceeding.**

---

## 5. Design Proposal: Version-Pinned Pattern Lookup

### 5.1 Problem with the Union Approach

The current design (Decision 1) proposes merging all known response markers into a
single regex: `r"[●⏺](?:...)*\s+"`. This has a compounding fragility problem:

- Each new Claude Code version may introduce new markers, prompt chars, or spinner
  formats.
- Merging them into one regex means every match attempt tests against ALL known
  variants simultaneously. A character that is a response marker in v2.1.62 might
  appear as normal content in v3.x, causing false extraction.
- There is no way to express "this pattern set is ONLY valid for this version range"
  in a union regex.
- Debugging is harder — when extraction fails or extracts the wrong thing, you can't
  tell which version's patterns were intended to match.

### 5.2 Proposed Alternative: Version-to-Pattern Registry with Floor Lookup

Instead of merging patterns, store each version's complete pattern set as a separate
entry. At runtime, resolve the pattern set by version:

1. **Exact match** → use that version's patterns.
2. **No exact match** → use the closest previous version (floor lookup).
3. **Env override** → `AGENTSYS_CAO_CLAUDE_CODE_VERSION` selects a version from the registry,
   bypassing auto-detection.

```
  LOOKUP ALGORITHM
  ════════════════

  Registry (sorted):    0.0.0    2.1.0    2.1.62    2.3.0  ...
                          │        │         │         │
                          ▼        ▼         ▼         ▼
                       [legacy] [prompt]  [marker]  [future]

  Query: "2.1.62"  →  exact match  →  returns "2.1.62" entry
  Query: "2.2.5"   →  no exact     →  floor("2.2.5") = "2.1.62"
  Query: "2.0.0"   →  no exact     →  floor("2.0.0") = "0.0.0"
  Query: "3.0.0"   →  no exact     →  floor("3.0.0") = "2.3.0"

  bisect_right on sorted version list, take index - 1.
```

### 5.3 Data Model

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ClaudeCodePatterns:
    """Complete pattern set for a Claude Code version range.

    Each field stores the raw data needed to compile regex patterns.
    The provider compiles these once during init.
    """

    # Response marker characters — each is tried as a line-start anchor
    # after optional ANSI. NOT merged into a character class.
    response_markers: tuple[str, ...]

    # Spinner/processing detection
    spinner_chars: str                  # character class contents
    spinner_requires_parens: bool       # whether \(.*\) suffix is required

    # Idle prompt characters and extraction stop
    idle_prompt_chars: tuple[str, ...]  # e.g. ("❯",) or (">", "❯")
    separator_pattern: str              # e.g. "────────"
```

Key point: `response_markers` is a **tuple of individual markers**, not a merged
character class. The provider tries each one sequentially when searching for the
last response. This means:
- Adding a new marker to a version entry can never accidentally match a different
  version's pattern.
- Each marker gets its own compiled regex anchored to line start.
- The extraction function iterates markers and picks the last match across all of
  them — same semantics as today, but with explicit per-marker matching.

### 5.4 Version Registry

```python
# Hardcoded in claude_code.py — edit this dict to support new versions.
# Each entry covers "this version and all subsequent versions until the
# next entry." Keys are version strings parseable by packaging.version.Version.
#
# !! Add new entries ABOVE the latest, not by modifying existing ones. !!

CLAUDE_CODE_PATTERN_VERSIONS: dict[str, ClaudeCodePatterns] = {
    #
    # Baseline — original CAO assumption. Covers all versions before 2.1.0.
    #
    "0.0.0": ClaudeCodePatterns(
        response_markers=("⏺",),               # U+23FA
        spinner_chars="✶✢✽✻·✳",
        spinner_requires_parens=True,            # old: "✽ Cooking… (esc to…)"
        idle_prompt_chars=(">",),
        separator_pattern="────────",
    ),
    #
    # v2.1.0 — ❯ prompt introduced alongside legacy > prompt.
    # (Approximate: use earliest version where ❯ was observed.)
    #
    "2.1.0": ClaudeCodePatterns(
        response_markers=("⏺",),               # still U+23FA
        spinner_chars="✶✢✽✻·✳",
        spinner_requires_parens=True,
        idle_prompt_chars=(">", "❯"),            # both prompt styles
        separator_pattern="────────",
    ),
    #
    # v2.1.62 — response marker changed to ●, spinner no longer
    # requires parenthesized suffix.
    #
    "2.1.62": ClaudeCodePatterns(
        response_markers=("●",),                # U+25CF
        spinner_chars="✶✢✽✻·✳",
        spinner_requires_parens=False,           # "✽ Razzmatazzing…" OK
        idle_prompt_chars=("❯",),                # > no longer used
        separator_pattern="────────",
    ),
}
```

### 5.5 Resolution Logic

```python
import bisect
import os
import re
from packaging.version import Version

# Pre-sorted at module load
_SORTED_VERSIONS: list[str] = sorted(
    CLAUDE_CODE_PATTERN_VERSIONS.keys(), key=Version
)
_LATEST_VERSION: str = _SORTED_VERSIONS[-1]

_ENV_OVERRIDE = "AGENTSYS_CAO_CLAUDE_CODE_VERSION"


def resolve_patterns(detected_version: str | None = None) -> ClaudeCodePatterns:
    """Resolve pattern set for a Claude Code version.

    Priority:
      1. Env var AGENTSYS_CAO_CLAUDE_CODE_VERSION (if set and non-empty)
      2. detected_version argument (from welcome banner)
      3. Latest registered version (fallback)

    Lookup: exact match first, then floor (closest previous version).
    """
    version_str = os.environ.get(_ENV_OVERRIDE, "").strip()
    if not version_str:
        version_str = detected_version or _LATEST_VERSION

    # Exact match
    if version_str in CLAUDE_CODE_PATTERN_VERSIONS:
        return CLAUDE_CODE_PATTERN_VERSIONS[version_str]

    # Floor lookup via bisect
    target = Version(version_str)
    idx = bisect.bisect_right(
        _SORTED_VERSIONS, target, key=Version
    )
    if idx == 0:
        # Older than anything we know — use baseline
        floor_key = _SORTED_VERSIONS[0]
    else:
        floor_key = _SORTED_VERSIONS[idx - 1]

    return CLAUDE_CODE_PATTERN_VERSIONS[floor_key]
```

### 5.6 Provider Integration

The `ClaudeCodeProvider` compiles patterns from the resolved preset once, replacing
the current module-level regex constants:

```
  CURRENT (module globals):              PROPOSED (instance attributes):
  ─────────────────────────              ──────────────────────────────

  RESPONSE_PATTERN = r"⏺..."  ──────▶   self._response_patterns: list[re.Pattern]
  PROCESSING_PATTERN = r"..."  ──────▶   self._processing_pattern: re.Pattern
  IDLE_PROMPT_PATTERN = r"..." ──────▶   self._idle_prompt_pattern: re.Pattern
                                         self._stop_pattern: re.Pattern
```

The compilation happens in `__init__`, and all methods (`get_status()`,
`extract_last_message_from_script()`, etc.) reference `self._*` instead of
module globals.

```
  INIT FLOW (with version detection)
  ═══════════════════════════════════

  __init__(...)
    │
    ├── self._patterns = resolve_patterns()     # default: latest
    ├── self._compile_patterns()                 # compile regexes
    │
    ▼
  initialize()
    │
    ├── wait_for_shell(...)
    ├── send_keys(claude command)
    ├── _handle_trust_prompt()
    │     │
    │     ├── detects "Claude Code v2.1.62" from banner
    │     ├── self._patterns = resolve_patterns("2.1.62")
    │     ├── self._compile_patterns()           # recompile if changed
    │     └── logger.info("Detected Claude Code v2.1.62, using pattern
    │          preset 2.1.62")
    │
    ├── wait_until_status(IDLE)                  # uses correct patterns
    └── self._initialized = True
```

The version detection is extracted from the existing banner match at line 137.
Currently it matches `Claude Code v\d+` — extend to capture the full semver:

```python
version_match = re.search(r"Claude Code v(\d+\.\d+\.\d+)", clean_output)
if version_match:
    detected_version = version_match.group(1)
    new_patterns = resolve_patterns(detected_version)
    if new_patterns is not self._patterns:
        self._patterns = new_patterns
        self._compile_patterns()
        logger.info(
            "Detected Claude Code v%s, selected pattern preset",
            detected_version,
        )
```

### 5.7 Env Override: Operational Escape Hatch

```
  AGENTSYS_CAO_CLAUDE_CODE_VERSION=2.1.62  cao-server
```

This pins the pattern set regardless of what the welcome banner says. Use cases:

- A new Claude Code version breaks auto-detection: pin to the last known-good
  version while investigating.
- Testing: force a specific version's patterns for unit tests.
- Multiple Claude Code versions running simultaneously on the same host (different
  tmux sessions) — env var can be set per-process or per-session.

The env var selects from the hardcoded registry. It does NOT accept arbitrary regex.
This is deliberate — writing correct extraction regexes requires understanding the
provider's internal assumptions. If someone needs a truly custom pattern set, they
edit `CLAUDE_CODE_PATTERN_VERSIONS` in the source.

### 5.8 Pattern Compilation Detail

The `_compile_patterns()` method builds regexes from the preset data. Each response
marker gets its own compiled pattern rather than being merged into a character class:

```python
ANSI_RE = r"(?:\x1b\[[0-9;]*m)*"

def _compile_patterns(self) -> None:
    p = self._patterns

    # One regex per marker — tried sequentially in extract/status methods
    self._response_res = [
        re.compile(rf"{ANSI_RE}{re.escape(m)}{ANSI_RE}\s+")
        for m in p.response_markers
    ]

    # Spinner: char class + ellipsis + optional parens
    parens = r".*\(.*\)" if p.spinner_requires_parens else ""
    self._processing_re = re.compile(
        rf"[{re.escape(p.spinner_chars)}].*…{parens}"
    )

    # Idle prompt — used in get_status() on ANSI-stripped text
    prompt_chars = "".join(re.escape(c) for c in p.idle_prompt_chars)
    self._idle_prompt_re = re.compile(rf"[{prompt_chars}][\s\xa0]")

    # Extraction stop — also applied to ANSI-stripped text
    self._stop_re = re.compile(rf"[{prompt_chars}][\s\xa0]")
    self._separator = p.separator_pattern
```

The extraction function then iterates `self._response_res` and collects all matches
across all markers, picking the last one. This replaces the current single-regex
approach:

```python
def extract_last_message_from_script(self, script_output: str) -> str:
    all_matches = []
    for pattern in self._response_res:
        all_matches.extend(pattern.finditer(script_output))

    if not all_matches:
        markers = ", ".join(self._patterns.response_markers)
        raise ValueError(
            f"No Claude Code response found - none of [{markers}] detected"
        )

    # Last match by position
    last_match = max(all_matches, key=lambda m: m.start())
    # ... rest of extraction (strip ANSI on stop-condition lines) ...
```

### 5.9 How to Add Support for a New Claude Code Version

1. Observe the new version's output format (response marker, spinner format,
   prompt character).
2. Add one entry to `CLAUDE_CODE_PATTERN_VERSIONS`:
   ```python
   "2.3.0": ClaudeCodePatterns(
       response_markers=("◆",),              # hypothetical new marker
       spinner_chars="✶✢✽✻·✳",
       spinner_requires_parens=False,
       idle_prompt_chars=("❯",),
       separator_pattern="────────",
   ),
   ```
3. Add unit tests with representative tmux output from that version.
4. The floor lookup automatically covers all versions between 2.1.62 and 2.3.0
   with the 2.1.62 patterns, and all versions >= 2.3.0 with the new patterns.
5. No regex merging, no union expansion, no risk of cross-version false matches.

### 5.10 Relationship to the Current Change

This proposal does **not** replace the current change's fix — it restructures how
the fix is expressed. Specifically:

| Current Design Decision          | How This Proposal Implements It              |
|----------------------------------|----------------------------------------------|
| D1: Accept both ⏺ and ●         | Two registry entries (0.0.0 and 2.1.62) with different `response_markers`. No union. |
| D2: Resilient spinner detection  | `spinner_requires_parens=False` on the 2.1.62 entry. |
| D3: Stop on ❯ prompts           | `idle_prompt_chars=("❯",)` on the 2.1.62 entry, compiled into `_stop_re`. Applied to ANSI-stripped lines (fixes gap G1). |
| D4: Runtime fallback hardening   | Unchanged — this proposal only affects the provider's pattern layer. |

The proposal also naturally addresses all three gaps from section 4:

| Gap | How Addressed |
|-----|---------------|
| G1 (ANSI on stop condition) | `_stop_re` is applied to ANSI-stripped lines in the new `extract_last_message_from_script()` |
| G2 (COMPLETED detection) | `get_status()` uses `self._response_res` (version-correct markers) for the COMPLETED check |
| G3 (relaxed processing + full history) | `spinner_requires_parens` is per-version, not globally relaxed; risk is bounded to the specific version |

### 5.11 Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Wrong version detected from banner (e.g., partial match, banner format changes) | `AGENTSYS_CAO_CLAUDE_CODE_VERSION` env override; fallback to latest if detection fails; log the detected version clearly |
| `packaging.version.Version` adds a dependency | Already in pip/setuptools transitive deps; alternatively use a simple tuple-based version compare |
| Instance attributes instead of module constants changes the call signature of methods used by `terminal_service.py` | No: `terminal_service.get_output()` calls `provider.extract_last_message_from_script(full_output)` through the provider instance, so instance attributes are naturally accessible |
| Per-version entries grow unboundedly | Practical limit is low (Claude Code releases major output format changes rarely); old entries can be pruned with a deprecation notice |

### 5.12 Summary

```
  BEFORE                              AFTER
  ══════                              ═════

  Module globals:                     Instance state:
  RESPONSE_PATTERN = r"⏺..."          self._patterns = resolved preset
  PROCESSING_PATTERN = r"...\(.*\)"   self._response_res = [compiled, ...]
  IDLE_PROMPT_PATTERN = r"[>❯]..."    self._processing_re = compiled
                                      self._idle_prompt_re = compiled
  ↓                                   self._stop_re = compiled
  One set of patterns for all         ↓
  versions, merged into union         Per-version patterns, selected by:
  regexes that grow over time           1. env override
                                        2. banner auto-detection
                                        3. floor lookup in version registry
```

**Recommendation:** Implement this as part of the current change, not as a follow-up.
The restructuring is modest (one dataclass, one dict, one lookup function, compile
method) and it eliminates the union-regex fragility from day one. The current tasks
list doesn't need to change much — task 1.1 becomes "implement version registry and
pattern compilation" instead of "update RESPONSE_PATTERN regex."
