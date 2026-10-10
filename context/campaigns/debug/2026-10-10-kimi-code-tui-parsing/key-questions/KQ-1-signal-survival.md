# KQ-1: Which text-scraping signals survive on kimi-code 2.1.1?

Date: 2026-10-10. Status: resolved (iteration 1, 2026-10-10). Owner: [iteration 1](../iterations/2026-10-10-plan-1-state-matrix-capture.md). Evidence: [session 1](../evidences/2026-10-10-session1-lifecycle-evidence.md), [session 2](../evidences/2026-10-10-session2-operator-surfaces-evidence.md).

Which hardcoded surface assumptions in the current kimi_code detector (`src/houmao/shared_tui_tracking/apps/kimi_code/profile.py`) and the server parser mapping (`src/houmao/server/tui/parser.py`) still match what kimi-code 2.1.1 renders, which are dead, and which states have no signal at all? Detector under test (corrected 2026-10-10, post-merge 8ad0854b): 2.1.1 resolves to `KimiCodeSignalDetectorV0_34_PLUS` (`detector_version=">=0.34.0"`, `activity_window_lines=4`, temporal growth disabled), not the fallback named at planning time. Product framing (directive 2026-10-10, see [debug intent](../debug-intent.md#user-facing-requirement-directive-2026-10-10)): the survival table is scored against the two user-facing booleans, ready-to-enter-prompt (`surface_accepting_input`) and accept-prompt (`surface_ready_posture`); the per-state propositions below exist to diagnose where those booleans break. Required evidence type: one frozen 5 fps terminal-recorder run driving the 2.1.1 state matrix, blind-labeled ground truth, and a replay of the resolved detector against those labels, producing a per-signal survival table with sample-ID citations.

## Critical Propositions

### KQ-1.1: Prompt and editor-box detection survives

`PROMPT_TOKEN_RE` (`^\s*[│┃]\s*>`), the `╭/╰/├/└` editor-box borders, and empty-prompt classification still match the 2.1.1 editor (source: `packages/pi-tui/src/components/editor.ts`, `components/editor/custom-editor.ts:832-897`; live-probe confirmed 2026-10-10). Test: detector `prompt_visible` / `prompt_text` agree with ground truth on at least 95% of labeled idle and editing samples. The `\x1b[2m` placeholder branch is expected dead (2.1.1 empty editor is `> ` plus inverse-space cursor) — `placeholder` style should never fire.

### KQ-1.2: Braille-activity detection fails; moon-activity survives

`ACTIVITY_LABEL_RE = /\b(working|thinking)\.\.\./` (profile.py:30) matches nothing in 2.1.1, which renders `Thinking…` / `Working…` capitalized with U+2026 (kimi-code `kimi-tui.ts:3503,3517`; live-probe confirmed). Because braille frames require the label (profile.py:516 post-merge), detector `active_evidence` is expected to be absent on ground-truth-active samples dominated by thinking/composing phases, while moon-spinner waiting/tool phases (no label required) are still detected. Test: per-phase miss rates against labeled busy sub-phase spans.

### KQ-1.3: Approval panels are detected; question and goal dialogs are not

The five `APPROVAL_HEADERS` and the `─`-rule bounded-panel rule survive unchanged, and the new option labels (`1. Approve once` … `4. Reject with feedback`) still satisfy `APPROVAL_CHOICE_RE` (live-probe confirmed). AskUserQuestion (` question` title, `[N]` options) and the goal-start prompt (`Approve CreateGoal?`, `Switch to … and start` options) match no approval pattern, so `ambiguous_interactive_surface` stays false while the agent is blocked. Test: detector approval/ambiguous fields vs ground truth on the labeled approval, question, and goal spans.

### KQ-1.4: Queue-hint and interrupt strings survive

The three `QUEUE_HINTS` are byte-identical in 2.1.1 (`components/panes/queue-pane.ts:31-34`) and interrupt strings (`Interrupted by user`, `Error: step interrupted (…)`) still match the detector's case-insensitive substring checks. Test: `pending_input` and `interrupted` agree with ground truth on labeled queue and interrupt spans.

### KQ-1.5: Footer-derived filtering is degraded but not harmful

`shift+tab:` is gone, `/model:` survives only as a rotating tip, `context:` persists with a new `(used/total)` suffix, and the footer is user-customizable via `[status_line]`. Expected effect: `_is_footer_line` / `_footer_model_thinking` misclassify nothing critical but the footer no longer provides stable auxiliary evidence. Test: audit whether any labeled busy sample's activity line is wrongly discarded as a footer line, and vice versa.

## Answer

Resolved by iteration 1 (two frozen 5 fps recordings, 1909 + 797 samples, blind-labeled, replayed under the `>=0.34.0` baseline and a monkey-patched 2.1.x candidate):

- **KQ-1.1 confirmed.** Editor/prompt detection survives: `PROMPT_TOKEN_RE` fired on 1894/1894 and 724/724 composer-usable samples with zero false fires in session 1; the `╭╰` box and `│ >` token are unchanged. The `\x1b[2m` placeholder branch is dead (2.1 empty editor uses an inverse-space cursor) but inert: the escape is pervasive elsewhere in 2.1.1 dim styling yet never on the prompt line, so it misclassifies nothing.
- **KQ-1.2 confirmed with refinement.** The legacy label regex matched 0/1561 active samples across both sessions; braille frames are discarded without it, so baseline `active_evidence` vanishes on thinking/working phases (139 false-ready samples in session 1, 254 in session 2 under the baseline). Moon frames cover only waiting/tool phases (80%/54%). The complete busy primitive is the spinner-frame union (moon OR braille at the live edge): 100% coverage on both sessions. The 2.1 label set (`Thinking…`/`Working…` with U+2026, `Retrying (N/M)`, `Compacting context…`, `Orchestrating…`, plus subagent rows `… Agent Running (…)`) is needed only to qualify braille frames.
- **KQ-1.3 confirmed.** All five approval headers and the choice regex survive on 2.1 option labels (58/58, zero false fires). The AskUserQuestion dialog is fully present as a surface signal (15/15) but matches no detector pattern; the goal-start prompt was not reached (unresolved, not refuted).
- **KQ-1.4 partially confirmed.** Queue hints and interrupt strings are byte-identical and fire on 100% of their spans, but both persist in scrollback (16 and 134 false-fire samples respectively), and the reducer's interrupted-over-active priority (`session.py:351`) converts notice persistence into sustained false-ready when a queued turn resumes after an interrupt. Verdict: degraded, needs the candidate's suppression guard (interrupt only counts without concurrent activity).
- **KQ-1.5 confirmed.** Footer filtering caused no observed harm; no activity line was discarded as a footer line in either capture. The footer is decoration under `[status_line]` customization and should not be a signal source.

Headline: on kimi 2.1.1 the current `>=0.34.0` detector produces false-ready on 139/1909 (session 1) and 254/797 (session 2) samples, including 100% of modal spans. The monkey-patched 2.1.x candidate (`scripts/explore/kimi-code-tui-parsing/campaign_lib/patches.py`, v3) reaches zero false-ready and zero false-busy on both sessions, with the two user-facing booleans at 99.2%/99.2% (session 1) and 100%/100% (session 2).

## Scope

Covers kimi-code 2.1.1 regular (scrollback) TUI mode in tmux on this host only, and only the detection layer (signals and public fields), not the tracker session state machine. The identification target is bounded by houmao's public state model (`models.py` `TrackedStateSnapshot`); kimi-internal states richer than that model (swarm rows, retry banners, compaction) are evaluated only for their effect on the public fields, never as states to identify (directive 2026-10-10). Does not cover fullscreen mode, does not evaluate escape-sequence or event-channel alternatives (KQ-2, KQ-3), and does not authorize any code change — the output is a measured survival table, not a patch.
