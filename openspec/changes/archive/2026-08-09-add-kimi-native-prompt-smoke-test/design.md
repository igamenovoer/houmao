## Context

See proposal.md for motivation. The parent change `use-kimi-native-system-prompt` is fully implemented and unit-tested; its remaining live-qualification tasks (5.3–5.5) need evidence that the native `SYSTEM.md` contract works against a real Kimi Code binary. The local machine has `kimi` 0.34.0 (confirmed via `kimi --version`) with native auto credential state in its Kimi Code home. The behavior-testing skill already froze the relevant case semantics in `skillset/dev/houmao-dev-behavior-testing/references/cases/native-prompt.md` (NSP-001 delivery, NSP-004 persistence); this change executes a smoke subset of those semantics as disposable scripts rather than the full 3-repetition case matrix.

The user has decided: scripts live in `tmp/<subdir>`, TUI labeling is delegated to a subagent, credentials come from Kimi auto discovery per the Houmao system skills, and scope is limited to proving the injected system prompt works from a Houmao agent profile to a real Kimi Code agent (headless and TUI) — not the full recorded-corpus qualification.

## Goals / Non-Goals

**Goals:**

- Prove end-to-end, with provider-native evidence, that a Houmao-managed Kimi brain launch projects the composed role prompt into `$KIMI_CODE_HOME/SYSTEM.md` and that Kimi 0.34.0 applies it before the first turn.
- Exercise both maintained launch surfaces: one headless turn and one unattended TUI session, plus one supported relaunch with digest comparison.
- Produce a frozen evidence bundle (bytes, digests, provenance, transcript, labeled TUI timeline) that the parent change's task 5.5 can cite.
- Keep everything disposable: no product code, no tests/ tree additions, no packaging impact.

**Non-Goals:**

- The full recorded-corpus qualification (parent tasks 5.3–5.4): no ≥5 dev + ≥3 held-out sessions, no strict/sparse replay matrix, no detector-profile maintenance decision.
- The full NSP case matrix: NSP-002 placeholder rejection and NSP-003 stale removal are already unit-tested hermetically and are not re-run live.
- CI integration or durable test infrastructure; these scripts are allowed to rot after qualification completes.
- Testing resume of pre-0.34 sessions or any CAO path.

## Decisions

### 1. Drive the real managed path through `houmao-mgr`, not internal APIs

The smoke scripts shell out to the supported `houmao-mgr` CLI (brain build, agent launch, headless turn, relaunch) exactly as an operator would. This tests the whole composition — launch-policy selection, brain construction, provider-start verification — instead of calling `ensure_kimi_system_prompt()` directly, which would only re-test what unit tests already cover.

Alternative considered: drive `houmao.agents` Python APIs in-process. Rejected because it bypasses the CLI validation layer and would not catch wiring regressions between CLI, launch plan, and projection helper.

### 2. Frozen-marker role with two-layer verification

The disposable role prompt embeds a unique frozen marker (a random token plus an unambiguous instruction, e.g. "You are the smoke-test sentinel; your assigned marker is KNS-<token>"). Verification is layered:

1. **Artifact layer (primary, pre-launch)**: assert managed `SYSTEM.md` exists with canonical bytes — leading `${base_prompt}`, effective-prompt suffix containing the marker, 0600 permissions; record effective and rendered SHA-256 digests; assert launch-plan/session provenance shows `native_home_system_prompt`, `KIMI_CODE_LEGACY_FLAG=0`, and successful precedence validation.
2. **Behavior layer (secondary, post-launch)**: submit "State your assigned role in one sentence." and judge the response for marker consistency with a forgiving matcher (token presence, not exact wording).

Per the NSP guardrails, a role-consistent answer alone never counts as proof; the artifact layer must pass first, and both layers are recorded.

Alternative considered: behavior-only probing. Rejected — it cannot distinguish native delivery from a bootstrap turn or a hallucinated role.

### 3. TUI session recorded at 20 Hz, labeled blind by a subagent

The unattended TUI run is captured with `pixi run python -m tools.terminal_record` at the canonical 0.05 s interval, snapshots frozen (`pane_snapshots.ndjson` digest recorded) before any labeling. A subagent then labels the 7 public tracked-state fields directly from the frozen snapshots, without seeing tracker output (blind labeling). The labeled timeline must show: startup → ready with no role-bootstrap chat turn, and evidence that projection completed before TUI startup.

Alternative considered: skip labeling and assert only on SYSTEM.md bytes for the TUI run. Rejected — the "no role-bootstrap turn" claim is a TUI-observable property that requires a labeled timeline, and the labeled session doubles as pilot evidence for the parent change's corpus task 5.3.

### 4. Relaunch checked by digest persistence, not re-probing

After the supported relaunch, the script compares pre- and post-relaunch `SYSTEM.md` digests and provenance. A matching digest plus fresh provider-start verification metadata satisfies NSP-004/relaunch semantics without a second paid prompt turn.

### 5. Kimi auto credentials imported from the native home

The smoke agent uses the credential state the installed `kimi` CLI natively discovers, per the Houmao system skills (`houmao-shared-routines->houmao-credential-mgr`, Kimi kind 4 "Existing Kimi Code Home"). Concretely: import the machine's resolved Kimi Code home (`$KIMI_CODE_HOME` or `~/.kimi-code`) into the scratch Houmao project with `houmao-mgr project credentials kimi add --code-home <native-home>`, then reference that credential when creating the specialist/agent. Posture is validated non-secretly before import: `kimi provider list --json` must show a configured provider and, when `config.toml` exists, `kimi doctor config` must accept it. Credential JSON and API-key values are never printed, logged, or copied into evidence; no `kimi login` or any auth-mutating flow runs. The imported bundle lives only under the scratch project's `.houmao/` tree inside the run root.

Alternative considered: use the fixture bundle `tests/fixtures/auth-bundles/kimi/personal-a-default`. Rejected per user direction — the smoke must prove the contract with the same auto credential an operator's real Kimi install uses, and the fixture bundle may not exist or may be stale on this machine. Alternative considered: pass the native home to the provider directly without Houmao import. Rejected because it bypasses the managed auth-bundle projection that is part of the launch contract under test.

### 6. Preflight hard-fail on environment

Before any live run, the script asserts: `kimi --version` parses and is ≥ 0.34.0, the native Kimi Code home resolves and shows a coherent auto credential posture per decision 5 (provider list non-empty, doctor config clean, no secret output), and the run root `tmp/kimi-native-prompt-smoke/<run-id>/` is writable. Failures abort before any quota is spent, credential imported, or tmux session created.

### 7. Product fix uncovered by the smoke: `bash -lc` pane wrapper

Live testing exposed that every tmux-backed headless turn and TUI launch failed on this machine: Houmao wrapped pane commands as `sh -lc <script>`, and with `/bin/sh` → dash the login profile chain (`/etc/profile.d/bash_completion.sh`) aborts before the script runs, so the pane died instantly and turn submission hung. The fix changes the wrapper to `bash -lc` in `headless_runner.py` (two sites) and `local_interactive.py` (one site), preserving login-shell PATH semantics. The pre-existing `test_headless_runner.py` suite failed on this machine for the same reason (5-minute timeout per case) and passes in seconds after the fix; its pane simulators were updated to `bash -lc` to match.

A second live finding is handled in the scripts rather than the product: a fresh managed Kimi home has no workspace-trust record for the launch workdir, so the Kimi TUI opens with a "Trust this folder?" modal that swallows pasted prompts. `run_tui.py` detects and accepts the modal once and records the intervention in evidence (consistent with the corpus spec's labeled-intervention contract). Whether Houmao should pre-seed trust for launch workdirs is a product question deferred to the parent change.

## Risks / Trade-offs

- [Native auto credential state is absent, expired, or scoped to a non-default OAuth host] → Preflight fails with an explicit diagnostic naming which posture check failed; no partial runs and no login attempt. If Kimi wrote a scoped token file (`credentials/kimi-code-env-<hash>.json`), the import is reported as unsupported rather than silently partial.
- [Evidence artifacts accidentally capture secret material] → Scripts record only variable names, file paths, and digests; transcripts are filtered for credential-shaped content before freezing.
- [Kimi response wording varies, making behavioral matching flaky] → The marker is a random high-entropy token; the matcher checks token presence, not phrasing. The artifact layer remains the primary oracle.
- [Live runs consume provider quota and can hit rate limits] → Exactly two paid prompt turns (headless + TUI) plus one relaunch digest check; no repetition matrix in smoke scope.
- [Subagent labeling may be imperfect] → Labeling is blind and the frozen snapshots are preserved, so any disputed label can be re-examined later; the smoke pass/fail does not depend on fine-grained label accuracy, only on the absence of a bootstrap turn before readiness.
- [Scripts under `tmp/` bit-rot as the product evolves] → Accepted; they are qualification evidence generators, not maintained tests. The parent change decides what graduates into durable coverage.

## Migration Plan

Not applicable for the smoke scripts (gitignored `tmp/` content; rollback is deleting the directory). The `sh -lc` → `bash -lc` runner fix is a behavioral repair with no migration surface: it restores the intended pane execution on systems where `/bin/sh` is dash; systems where `sh` already resolves to a bash-compatible login shell are unaffected.
