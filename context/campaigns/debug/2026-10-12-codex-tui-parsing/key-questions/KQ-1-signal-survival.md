# KQ-1: Which text-scraping signals survive on codex 0.162.1?

Status: resolved 2026-10-12. Iteration owner: [iteration 1](../iterations/2026-10-12-plan-1-state-matrix-capture.md). Evidence: [session 1](../evidences/2026-10-12-session1-lifecycle-capture.md), [session 2](../evidences/2026-10-12-session2-operator-surfaces-capture.md).

## Opening Statement

The codex_tui detector's text-scraping assumptions were built against 0.116.x live surfaces and 0.144.x recorded surfaces. Codex 0.162.1 renders differently in at least three confirmed places (interrupt suffix, completion-marker prefix, composer boxing). This question enumerates every hardcoded signal family in `src/houmao/shared_tui_tracking/apps/codex_tui/` and asks, per family: does it still fire correctly on 0.162.1 surfaces, and does it stay silent on surfaces where it must not fire?

## Critical Propositions

### P1.1 Composer / prompt-area extraction

`_CODEX_PROMPT_RE` (`^\s*›(.*)$`) and the prompt-behavior variants (`CodexPromptBehaviorVariantV0_116_X`, `V0_144_X`, fallback) classify the prompt area. On 0.162.1 the composer is unboxed (`› Ask Codex to do anything`, no border) and transcript lines echo user prompts with the same `›` token. Proposition: prompt-area extraction misidentifies transcript echoes as the composer, or placeholder/draft classification drifts, on 0.162.1. Confirmed surviving or broken by replay against labeled captures.

### P1.2 Activity status row

Live recon shows `• Working (2s • esc to interrupt)` and a footer braille spinner while busy; source format string `Working (Ns • esc to interrupt)` survives (`status_indicator_widget.rs:452`). Proposition: the existing status-row regexes (`^\s*• (.+?) \((.+esc to interrupt.*)\)`, collaboration-cell and queued-follow-up families) still detect busy on 0.162.1, including during tool calls (`• Calling `, `• Running `) and MCP boot (`Booting MCP server:`).

### P1.3 Completion marker

Detector prefix `─ Worked for ` vs live `  Worked for 3s • 3:30 AM`. Proposition: completion-marker detection is broken on 0.162.1 (prefix drift); the marker's new exact shape is stable across turns.

### P1.4 Interruption and steer handoff

Detector strings `Conversation interrupted - tell the model what to do differently. ` and `Model interrupted to submit steer instructions.` vs 0.162-era `■ Conversation interrupted - use /feedback if something went wrong`. Proposition: user-interrupt detection is broken on the suffix drift; steer-handoff detection is unverified (text survival unknown).

### P1.5 Approval surfaces

Overlays key on `Would you like to run the following command?`, `…make the following edits?`, `…grant these permissions?`, `Press enter to confirm or esc to cancel`, plus selection popups (`Select Model and Effort`, `Select Approval Mode`, etc.). All still present in source; a new surface `Would you like to send input to the existing terminal?` is uncovered. Proposition: known approval headers still match by exact string; the new send-input surface and any restyled option lists read as idle/unknown (false-ready risk).

### P1.6 Terminal failure surfaces

Error-cell regexes cover stream disconnect, server errors, context length, remote compaction, unknown parameters, reconnecting, background-terminal waits. Proposition: these families' rendered text on 0.162.1 still matches the regex inventory; degraded-context diagnostics still attach correctly.

### P1.7 Startup surfaces

Trust-directory prompt (`onboarding/trust_directory.rs`), update notifier, and the `⚠ N warning · f2 to view` footer indicator. Proposition: cold-start in an untrusted workdir shows a trust surface the current detector does not classify as a blocking overlay (false-ready during startup).

## Answer / Resolution

Resolved by iteration 1 (2026-10-12). Signal-level verdicts from the labeled audits (fired/missed/false-fired counts in the evidence docs):

- **P1.1 — surviving with a modal-shield caveat.** Last-`›`-line anchoring correctly finds the unboxed composer despite `›`-echoed transcript lines; the 0.144.x render-state classification (dim = placeholder, plain = draft) still works (`editing` family fully correct under the 0.144.x arm). But on modal surfaces (trust screen, approval, picker) the last `›` line is the modal's selected option, so the bare token regex false-fires (50 false fires in session 1) unless modal surfaces are masked first.
- **P1.2 — degraded.** The status-row regex matches `• Working (Ns • esc to interrupt)` exactly (445/549 active samples in session 1, zero false fires) — but the row blinks off for 1-2 samples mid-turn (redraw) and hides entirely while the final answer streams (16 s in the queue turn). The shipped `detect_activity` also checks `_is_assistant_response_line` *before* the status regex, so any non-hardcoded status label (`• Compacting context (Ns • esc to interrupt)`) is misclassified as prose — compaction read as `ready` 88/88 samples. Footer braille spinner is not line-anchored and collides with the splash logo's braille art (0/549 fired, 24 false fires) — unusable as a text signal.
- **P1.3 — broken.** `─ Worked for ` never fires (0/1207 success samples). The prefix-free `Worked for ` form is stable across all five captured turns and denial turns do not dock at all (they end in the interrupted notice).
- **P1.4 — broken (interrupt), unverified (steer).** The legacy two-sentence interrupt text never fires (0/115). The 0.162 prefix `Conversation interrupted` (live-edge scoped) is 115/115 with zero false fires in session 1. `Model interrupted to submit steer instructions.` never renders in 0.162.x — a mid-busy follow-up is absorbed silently (no steer text; single `Worked for` covers both).
- **P1.5 — mixed.** Approval headers + `Press enter to confirm or esc to cancel`: surviving (28/28, zero false). The numbered-option regex fires on modals but also on any numbered list (63 false fires). The picker popup title `Select Model and Effort` survives but the list-selection *footer* needle (`Press enter to confirm or esc to go back`) is dead — 0.162 renders `enter select · esc back` — so picker detection failed 13/13. Send-input approval surface not reached (coverage gap; needle added to the candidate untested-by-capture but source-backed).
- **P1.6 — unresolved.** No error/retry surface was capturable without fault injection; declared coverage gap.
- **P1.7 — confirmed gap, fix qualified.** The trust screen was fully undetected (46/46 session-1, 50/50 session-2 false-ready-ish under both baselines). The candidate's `Trust this folder?` + `Trust and continue` needle is 96/96 with zero false fires. New finding: the trust screen renders even under `--dangerously-bypass-approvals-and-sandbox` for untrusted git-repo workdirs, so unattended flows meet it too.

The appropriate parse per state (carried to the [repair report](../reports/2026-10-12-codex-0-162-x-parsing-repair.md)): text scraping on the 0.144.x skeleton with the candidate's needle/ordering/temporal repairs recovers both user-facing booleans at 99.8%/100% (session 1) and 100%/100% (session 2). Escape sequences carry nothing (zero OSC). The rollout event stream is the viable oracle (Arm C), not a TUI replacement.

## Scope

Covers text-scraping signal survival only (Arm A1/A2 of the owning iteration). Escape-sequence channels are out of scope here (audit lives in iteration 1 as Arm B but feeds no KQ unless signals survive); structured channels are [KQ-2](KQ-2-structured-channels.md). Scoring follows the owning iteration's predeclared decision rules (surviving / degraded / broken / unresolved).
