# KQ-1: Which text-scraping signals survive on claude 2.1.296?

Status: resolved 2026-10-12. Iteration owner: [iteration 1](../iterations/2026-10-12-plan-1-state-matrix-capture.md). Evidence: [session 1](../evidences/2026-10-12-session1-lifecycle-capture.md), [session 2](../evidences/2026-10-12-session2-operator-surfaces-capture.md).

## Opening Statement

The claude_code detector's text-scraping assumptions were qualified against Claude Code surfaces around 2.1.81. The installed 2.1.296 is 215 patch versions later, still inside the maintained [2.1.0, 2.2.0) interval, so drift is invisible by construction. A pre-campaign string audit of the installed bun binary already refutes one load-bearing signal (P1.4 below). This question enumerates every hardcoded signal family in `src/houmao/shared_tui_tracking/apps/claude_code/` and asks, per family: does it still fire correctly on 2.1.296 surfaces, and does it stay silent on surfaces where it must not fire?

## Critical Propositions

### P1.1 Prompt-area extraction

`build_prompt_area_snapshot` anchors on the last `❯` line (`_CLAUDE_PROMPT_RE = ^\s*❯(.*)$`), and `pending_input_state` requires a complete composer frame of `─` rule lines above and below the prompt (`signals/pending_input.py:92-96`). Proposition: the `❯` anchor and boxed-composer structure survive on 2.1.296, or the composer has been restyled (unboxed, re-tokened) the way codex's was.

### P1.2 Ghost-suggestion style classification

Placeholder-vs-draft classification keys on semantic SGR style: ghost suggestion = fg 231 / bg 237, any-plain = draft, any-dim = placeholder (`signals/prompt_behavior.py:112-149`). Proposition: 2.1.296 still renders the composer placeholder and ghost suggestions with these exact color codes; a theme or renderer change breaks classification silently into `unknown`.

### P1.3 Activity signals

Busy detection keys on the spinner-line family `^[✢✻✽✶·*]\s+.+…` and the `esc to interrupt` footer (`FOOTER_INTERRUPT_RE`), plus `● ` active-block lines. The binary still carries `esc to interrupt` (2 hits). Proposition: the spinner glyph set and footer text still render while busy; spinner verbs or glyphs may have drifted the way codex's status labels did.

### P1.4 Completion marker

Detector regex `Worked for \d+[smh]` (`profile.py:28`). The binary contains zero `Worked for` occurrences; instead it carries `Vc=["Baked","Brewed","Churned","Cogitated","Cooked","Crunched","Sautéed","Worked"]` with per-session hash selection (`Yc(m)>>>0 % Vc.length`), default `FN="Worked"`, and a setting `Show "Cooked for Nm Ns" after each assistant turn`. Proposition (pre-refuted by the audit, confirmed quantitatively by capture): hardcoded `Worked for` fires in only the sessions whose hash picks `Worked`; the surviving needle is a bounded verb-set pattern `<verb> for <dur>` matched against the eight known verbs, never a full literal (standing needle-style directive). Open sub-question: whether the marker docks as a transcript line, a footer element, or both.

### P1.5 Interruption surface

Detector regex `^⎿\s+Interrupted · What should Claude do instead\?$` (`profile.py:30`). The binary carries the suffix (3 hits) plus a changelog line about fixing that hint's appearance. Proposition: the interrupted screen still renders this shape; prefix token and layout unverified until capture.

### P1.6 Known-failure color heuristic

`profile.py:121-134` flags known failure when the latest `⎿` status line carries non-246 colors that also appear in the footer. Proposition: error surfaces (API errors, overload, rate limit) still render in a shared non-246 color on 2.1.296; the heuristic's premise (footer shares the error color) still holds. Likely unreachable without relay faults — declared opportunistic.

### P1.7 Queued-input preview

`pending_input_state` requires a boxed composer plus a non-empty, indented, ghost-styled `❯` cell directly above its upper rule. The binary carries 567 `queued` string hits. Proposition: typing and submitting a follow-up while busy renders this preview structure on 2.1.296; ghost-style dependence inherits P1.2's risk.

### P1.8 Operator and startup surfaces

The detector has no approval-overlay needle inventory comparable to codex's; it handles slash-menu ambiguity and a startup footer advisory that the binary audit shows is dead (P-readiness: `READY_FOOTER_ADVISORY_PATTERNS` strings absent from the binary). Session 2 captures: command approval, edit approval, `/model` picker, trust dialog. Proposition: these surfaces read as false-ready or false-idle under the current detector; their 2.1.296 shapes are enumerated for a needle inventory.

## Answer / Resolution

Resolved by iteration 1 (2026-10-12). Per-proposition verdicts with fired/missed/false-fired counts in the evidence docs' signal-audit tables:

- **P1.1 — surviving with the modal-shield caveat.** The composer stays boxed (`─` rules, 1497/1498 in session 1; 260/260 in 002) and the last-`❯` anchor finds it. But every modal renders a `❯`-option line (trust `❯ No, exit`, picker `❯ 5. Sonnet ✔`, approvals `❯ 1. Yes`), so the bare token false-fires on 64 (session 1) and 843 (002) samples — modals must be masked before prompt classification, the codex P1.1 disease repeated.
- **P1.2 — degraded.** Ghost styling (fg 231 / bg 237) still marks the composer region (1422/1443 in session 1), but the `Try "…"` placeholder *text* renders only on the fresh composer (19/1443); post-turn empty composers are bare `❯`. On modal-heavy surfaces the ghost colors false-fire (780 in 002 — dialogs reuse the highlight palette), so ghost style cannot be trusted without modal masking.
- **P1.3 — mixed.** The busy footer suffix `· esc to interrupt ·…` is the best signal (741/744 session 1, 76/76 in 002, zero false fires). The spinner regex is degraded-to-broken: 2.1.296 renders both `· Calculating… (10s · ↓ 38 tokens)` (matches) and the suffix-less `✻ Cerebrating… ` (trailing space, no parenthetical — regex cannot match; 3/76 in 002), and the spinner hides during answer streaming. Gerund verbs are a second randomized family (`Calculating`, `Ebbing`, `Blanching`, `Cerebrating` observed).
- **P1.4 — broken, as pre-refuted.** `Worked for` fired 0/646 success samples. The dock is `✻ <Verb> for <dur> · done <time>` with per-turn randomized verbs (Cooked, Sautéed, Cogitated, Baked, Churned captured) and `Nm Ns` durations. The verb-set pattern hits 646/646 but false-fires 740 from scrollback persistence — it needs dock-position/live-edge scoping.
- **P1.5 — degraded with a silent-abort hole.** The detector's full-line regex (applied to stripped lines) matches when the line is visible (confirmed by direct probe on s001533). But Esc mid-turn aborts **silently** — no `⎿ Interrupted` line at all, and the prompt is restored into the composer as a draft (23/61 session-1 misses). The line renders only for C-c/approval-denial/slash-preemption interruptions, then persists in scrollback (801 false fires unscoped in 002).
- **P1.6 — unresolved.** No error/retry surface occurred on the relay; declared coverage gap.
- **P1.7 — broken.** The ghost-styled echo cell above the composer never renders. 2.1.296's queued surface is the composer placeholder `Press up to edit queued messages` (s000957–s000968), after which the follow-up echoes into the transcript as a `❯` user block and merges into the running turn (single dock covers both — steer-merge semantics, like codex).
- **P1.8 — confirmed gap, shapes enumerated.** The detector has no modal inventory: trust dialog, `Select model` picker, and both approval dialogs (`Do you want to proceed?` with `1. Yes / 2. No`; `Do you want to create <name>?` with `Yes, and always allow access…`) all read as ready/composer-usable. Session 2's boolean agreement collapses to 0.24/0.17 for exactly this reason. New platform finding: 2.1.296's default permission mode is **auto mode**, which auto-approves low-risk actions without any dialog; deterministic approval capture requires `permissions.ask` rules.

Headline boolean agreement (per-sample vs blind labels): session 1 — accepting 0.9584 / ready_posture **0.4875** (50 false-ready, 7 false-busy); session 2-002 — accepting **0.2355** / ready_posture **0.1667** (843 false-ready); session 2-001 — accepting 0.9657 / ready_posture 0.4920. Arms A1 (maintained 2.1.x) and A2 (fallback) score identically to within 0.04 on every field — the fallback earns nothing; the kimi/codex registry posture (floor + no fallback) is the right disposition.

## Scope

Covers text-scraping signal survival only (Arms A1/A2 of the owning iteration). Escape-sequence channels: audited as iteration 1's Arm B — zero OSC 133 / OSC `9;4` in all 4531 samples across three sessions; no KQ opens for them. The transcript store is [KQ-2](KQ-2-transcript-oracle.md). Scoring followed the owning iteration's predeclared decision rules (surviving / degraded / broken / unresolved).
