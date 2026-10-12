# Debug Intent: Claude Code TUI Parsing

Date: 2026-10-12. Status: iteration 1 complete (KQ-1 resolved, KQ-2 answered — transcript oracle confirmed, no live channel exists); post-repair candidate qualified 2026-10-13 against re-frozen labels (booleans 1.0000/1.0000, 1.0000/1.0000, 1.0000/0.9995 across the three frozen sessions, zero false-ready; see the repair report's Candidate Qualification section); repair proposal awaiting manual review in [reports/2026-10-12-claude-2-1-296-parsing-repair.md](reports/2026-10-12-claude-2-1-296-parsing-repair.md). Campaign directory: `context/campaigns/debug/2026-10-12-claude-code-tui-parsing/`.

## Problem Statement

Houmao tracks CLI agent state by scraping terminal surfaces. Its claude_code detector (`src/houmao/shared_tui_tracking/apps/claude_code/`) ships one maintained profile — `ClaudeCodeSignalDetectorV2_1_X`, registry interval [2.1.0, 2.2.0) (`src/houmao/shared_tui_tracking/registry.py:122-129`) — plus a silent `FallbackClaudeDetector` that catches every other version (`registry.py:130-136`). The launch policy `src/houmao/agents/launch_policy/registry/claude.yaml` was live-probed on Claude Code 2.1.81 (strategy `claude-unattended-2.1.81`, `supported_versions: ">=2.1.81"`).

The currently installed claude is `2.1.296` (verified `claude --version` on this host, 2026-10-12; bun-compiled single-file binary `~/.bun/install/global/node_modules/@anthropic-ai/claude-code-linux-arm64/claude`, 256 MB, dated 2026-10-10). Unlike codex (which sat outside every maintained interval), 2.1.296 resolves to the *maintained* 2.1.x profile with no warning — so any drift since the 2.1.81-era qualification is invisible by construction. A pre-campaign string audit of the installed binary already confirms drift in at least one load-bearing signal (see Starting Evidence). The campaign question: what is the appropriate way to determine claude 2.1.296 turn state (idle, editing, busy, approval pending, queued input, interrupted, exited) — repaired text scraping, escape-sequence channels, or the provider's own session transcript store?

## User-Facing Requirement (carried over from the kimi campaign, directive 2026-10-10)

The downstream user does not need a fine-grained state taxonomy. The product contract is two coarse booleans about the TUI surface:

1. **Ready to enter prompt**: the operator can type into the TUI right now (the composer accepts keystrokes). Maps to `surface_accepting_input` (editing facet: `surface_editing_input`).
2. **Accept prompt**: a prompt submitted now starts processing immediately instead of sitting in the provider-owned queue because the agent is busy. Maps to `surface_ready_posture`, adjudicated operationally.

Fine-grained states remain diagnostic observables only; success and repair priority are judged on the two booleans.

## Detection Target Boundary (carried over)

The detection target is houmao's existing public state model, `TrackedStateSnapshot` / `TrackedTimelineState` (`src/houmao/shared_tui_tracking/models.py`). Claude-internal states (todo lists, subagent/Task activity, MCP boot, auto-compaction, retry countdowns, permission-rule nags) enter the evaluation only as interference: they must leave the public fields correct and never manufacture a false `ready` or false `idle`. The campaign proposes no new public fields.

## Credential and Cost Lane (user directive 2026-10-12)

All live testing launches through the user's OpenLux relay launcher `~/.local/bin/claude-openlux-0.5x`:

- Wraps `~/.bun/bin/claude` (2.1.296) with `ANTHROPIC_BASE_URL=https://api.openlux.ai` and `ANTHROPIC_AUTH_TOKEN` from `~/.local/bin/openlux-api-key`; unsets `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, and all model pins; sets `API_TIMEOUT_MS=300000`, `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`, `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`; patches `~/.claude.json` `hasCompletedOnboarding`; appends `--dangerously-skip-permissions`; passes `"$@"` through to claude.
- The relay bills real money per token. **All LLM-driving prompts run under the sonnet model** (user directive 2026-10-12). The launcher clears env model pins, so model selection is the pass-through `--model sonnet` CLI arg, verified inside the TUI at session start (bootstrap operation in iteration 1). If the relay rejects or silently upgrades the model, the run stops before driving and the user is consulted — no silent spend.
- Cost discipline: exactly two recorded sessions, short prompts, recordings reused across all analysis arms; no exploratory sessions beyond the plan.
- Credential hygiene: `openlux-api-key`, `~/.claude/.credentials.json`, tokens, and any credential material are never read, printed, copied, or embedded in artifacts. Transcript JSONL files under `~/.claude/projects/` are read-only oracle inputs (they contain conversation content, not credentials); campaign artifacts may quote event structure and timestamps, never full prompt payloads beyond what the scenario itself authored.

## Starting Evidence

Version/registry posture (verified by inspection):

1. `registry.py:122-136`: claude intervals [2.1.0, 2.2.0) (profile `2.1.x`) plus an unconditional fallback. 2.1.296 is in-interval, so the maintained profile claims it with no qualification evidence past 2.1.81.
2. The silent-fallback disease cured for kimi (`openspec/changes/archive/2026-10-12-raise-kimi-code-floor-2-1-1/`) and codex (commit `0ddd4868`, floor at 0.162.1, no fallback, `UnsupportedToolVersionError` below floor) is still live for claude.
3. `claude.yaml` launch policy claims `>=2.1.81` with probe evidence from 2.1.81; nothing re-qualified launch or tracking at 2.1.296.

Binary string audit (2026-10-12, `grep -a` on the installed bun binary; string-level evidence, no source tree exists for claude):

4. **Completion marker refuted before capture**: the detector keys on `Worked for \d+[smh]` (`apps/claude_code/profile.py:28`), but the binary contains zero `Worked for` occurrences. Instead it carries a randomized verb list `Vc=["Baked","Brewed","Churned","Cogitated","Cooked","Crunched","Sautéed","Worked"]` with per-session hash selection and default `FN="Worked"`, plus a setting described as `Show "Cooked for Nm Ns" after each assistant turn`. The hardcoded regex fires only in sessions whose hash lands on `Worked` — a ~1/8 hit rate by construction. The replacement needle must be a bounded verb-set pattern, never the full literal (standing needle-style directive).
5. Interrupt suffix `What should Claude do instead?` survives in the binary (3 hits, including a changelog line referencing a fix to that hint on the interrupted screen); `esc to interrupt` survives (2 hits). Rendering on live surfaces is unverified — iteration 1 measures.
6. Footer advisory `READY_FOOTER_ADVISORY_PATTERNS` (`Claude Code has switched from npm to native installer.` / ``Run `claude install` ``) has zero hits (`Try claude install` absent); the advisory family is likely dead code at 2.1.296.

Detector inventory under test (all in `apps/claude_code/`): `❯` prompt anchoring with `─` composer rules and ghost-suggestion SGR style classification (fg 231 / bg 237) for placeholder-vs-draft (`signals/prompt_behavior.py`); spinner-line family `^[✢✻✽✶·*] …` and `esc to interrupt` footer for activity; `⎿ Interrupted · What should Claude do instead?` for interruption; a color-246-exclusion known-failure heuristic; boxed-composer queued-preview detection (`signals/pending_input.py`); slash-menu ambiguity handling.

Fixture poverty: `tests/fixtures/shared_tui_tracking/` holds codex and kimi_code corpora only — no claude fixture exists at all. The older `scripts/explore/claude-code-state-tracking/` harness is a pre-server demo (passive recording, ReactiveX tracker) and is historical reference, not a campaign vehicle.

Structured channel worth oracle-testing (claude-specific): the session transcript store `~/.claude/projects/<workdir-slug>/*.jsonl`, written live by the TUI. Claude ships no app-server or attach protocol, so there is no live-oracle proposition — transcripts are a post-hoc oracle only.

## Comparison Arms

| Arm | Approach | What is evaluated |
| --- | --- | --- |
| A1 | Current `2.1.x` profile replay (what 2.1.296 resolves to today) | Baseline mismatch catalog vs blind ground truth |
| A2 | `FallbackClaudeDetector` replay via observed-version override | Control: is the fallback actually worse than the stale maintained profile? |
| B | Escape-sequence audit (OSC 133 / OSC 9;4 and friends) on escape-preserving captures | Presence/absence by state; claude's renderer survival unknown |
| C | Session transcript JSONL inventory (`~/.claude/projects/`) from the same sessions | Oracle for validating Arms A; timestamp alignment to labeled spans |

One recording feeds Arms A1, A2, and B; Arm C reuses provider-side artifacts of the same sessions. Cost discipline: no extra capture beyond the two planned sessions.

## Scope and Implementation Boundary

In scope: Claude Code 2.1.296 interactive TUI behavior as rendered in tmux on this host through the OpenLux relay; the houmao claude_code detector profiles, registry version selection, and terminal_record analyze path as analysis subjects; recording/replay tooling and fixture capture into this campaign's `evidences/`.

Methodology — record first, test second (identical to the codex campaign): every live probe is recorded with the repo's terminal recorder (`pixi run python -m tools.terminal_record start --mode active --tool claude --sample-interval-seconds 0.2`, 5 fps per the standing user directive; captures escape sequences). Analysis and labeling run offline against frozen recordings. Ad-hoc tmux `capture-pane` probes are reconnaissance only, not evidence.

Binding rules adopted from `skillset/dev/houmao-dev-tui-testing` and `skillset/dev/terminal-recorder-workflow` (same as the codex campaign):

1. Launches: session 1 runs the `claude-openlux-0.5x` launcher as-is with `--model sonnet`; session 2 replicates the launcher's environment lane but omits `--dangerously-skip-permissions` so approval surfaces render (documented deviation; same relay, key, model, timeout). Houmao's own claude launch policy is not the vehicle here — it would inject a managed `CLAUDE_CONFIG_DIR` and conflict with the user-specified launcher. A confirmation prompt during a bypass-mode run is a failed or incomplete test, recorded as such.
2. Recording starts before the first operation and stops explicitly; the run is frozen with SHA-256 digests before any labeling or replay. Failed or tainted attempts are preserved, never deleted.
3. Artifact authority: `pane_snapshots.ndjson` is the machine replay source of truth; `labels.json` is independent ground truth; tracker/analyze output is implementation output, never ground truth.
4. Blind-label boundary: ground truth authored from raw recordings alone, using the eight public tracked-state fields from `skillset/dev/houmao-dev-tui-testing/references/state-labeling.md` (including the modal convention from the kimi campaign), with complete non-overlapping sample coverage.
5. Tracker-blind driving: scenario steps use `send_text`, `send_key`, `wait_seconds`, and direct documented `wait_for_pattern` only.
6. Cadence: 5 fps per standing user directive; if a key question needs cadence-sensitivity above 5 Hz, record that iteration's source at 20 Hz and derive down, naming the deviation.

`extern/orphan/` remains read-only (no claude source exists there; the audit lane is string-grep on the installed binary, which is weaker evidence than a source tree and is classified accordingly). Production code under `src/houmao/` remains read-only for the duration of the campaign. Experiment tooling lives in `scripts/explore/claude-code-tui-parsing/` (monkey-patching production seams at runtime, codex precedent); candidate repairs are exercised there only. Integration into `src/houmao/` happens only after manual review of the campaign's reports; this campaign produces no OpenSpec artifacts and modifies nothing under `openspec/`.

Out of scope: codex and kimi_code detector profiles; claude headless (`claude -p`) as a launch-mode change; CAO provider work; changes to claude configuration beyond probe setup; implementation of any fix in `src/houmao/`.

## Success Criteria

Resolution means the following are answered with evidence under `evidences/` and synthesis in `reports/`:

1. A validated signal set (per arm) that decides both user-facing booleans on claude 2.1.296 across the driven state matrix, with fine-grained states as diagnostic coverage for where each boolean flips.
2. Each signal's reliability classified (stable / version-fragile / unreliable), with the exact 2.1.296 capture proving it.
3. A recommendation naming the appropriate parsing approach per state, ready to become an implementation proposal and the first fixture corpus for `tests/fixtures/shared_tui_tracking/claude/`.
4. A disposition on claude registry posture: whether to mirror kimi/codex (floor at the qualified version, no fallback, `UnsupportedToolVersionError` below floor) and how launch policy `supported_versions` realigns, given that this campaign qualifies 2.1.296 while the launch policy was probed at 2.1.81.

## No-Product-Change Declaration

This campaign is an isolated diagnostic. It does not authorize changing production code under `src/houmao/`, test fixtures under `tests/`, anything under `openspec/`, or claude's own configuration files beyond temporary probe needs. Findings feed a later integration, gated on manual review of `reports/`.

## Key Questions and Iterations

- [KQ-1: Which text-scraping signals survive on claude 2.1.296?](key-questions/KQ-1-signal-survival.md) — resolved 2026-10-12 (survival table + per-proposition verdicts in the answer).
- [KQ-2: Can the claude session transcript store serve as the state oracle?](key-questions/KQ-2-transcript-oracle.md) — answered 2026-10-12 (post-hoc oracle confirmed; ≤0.21 s seam alignment; no live channel exists).
- [Iteration 1: claude 2.1.296 state-matrix capture and detector gap analysis](iterations/2026-10-12-plan-1-state-matrix-capture.md) — complete 2026-10-12; gates passed with declared gaps (compaction, tui_down, error/retry surfaces).
- Synthesis: [claude 2.1.296 parsing repair report](reports/2026-10-12-claude-2-1-296-parsing-repair.md) — fix list + baseline qualification scores, awaiting manual review before any integration.
