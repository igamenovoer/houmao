# KQ-1: Unattended Trust and Injection

Status: resolved (iteration 1, 2026-10-20; all four propositions answered on the openlux lane). Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

Can houmao's observer hooks be injected into a Codex launch such that they execute with **zero user action in unattended TUI mode**, and which injection variant is the right one for the managed path?

Source baseline (`extern/orphan/codex` @ `0910087`): handlers install only when `enabled && (bypass_hook_trust || managed || trusted_hash == current_hash)` (`codex-rs/hooks/src/engine/discovery.rs:810`); the trust modal is TUI-only (`codex-rs/tui/src/startup_hooks_review.rs`); untrusted hooks are silently skipped everywhere else. Managed codex launches already own a synthesized runtime home (`src/houmao/agents/launch_policy/registry/codex.yaml`).

## Propositions

### P1.1 Bypass-flag arm runs hooks unattended

A launch with `$CODEX_HOME/hooks.json` (or runtime-home `config.toml [hooks]`) plus `--dangerously-bypass-hook-trust` executes the observer hooks in unattended TUI mode with no trust modal and no startup regression. Test: S0/S1 launch with the flag; verify `SessionStart` arrives within the startup grace and the pane reaches the ready composer without any keypress.

### P1.2 Pre-trusted-hash arm runs hooks unattended

A launch without the bypass flag but with `[hooks.state."<key>".trusted_hash]` pre-written into the runtime-home `config.toml`, using a local reimplementation of Codex's normalized-hash algorithm (SHA-256 over compact JSON of the normalized handler, `codex-rs/hooks/src/engine/discovery.rs:874` + `codex-rs/config/src/fingerprint.rs:71`), executes hooks unattended. Test: compute the hash offline, launch, verify `SessionStart` arrives; then perturb the command and verify the hook stops running (proves the hash is the trust mechanism, not a fluke).

### P1.3 Control: no-trust failure mode is documented

A launch with hooks but neither bypass nor pre-trust shows the trust modal in the TUI (which would hang an unattended session) or silently skips hooks. Test: S2 control session; record pane state, whether any keypress was required, and whether `SessionStart` ever arrives; then exercise the modal's "trust all" to confirm it writes `hooks.state` entries (validating the key format P1.2 must reproduce).

### P1.4 Session-flags (`-c`) injection arm

`-c 'hooks.SessionStart=[...]'` style overrides inject hooks without touching the runtime-home files, and compose with the bypass flag. Test: one launch using only `-c` injection; verify `SessionStart` arrives. Record whether the managed launch's canonicalization of caller `-c` overrides (codex.yaml: "Caller launch args and config overrides that target unattended-owned no-prompt surfaces are canonicalized away") would interfere on the managed path.

## Answer

Iteration 1, 2026-10-20, all four arms run at codex-cli 0.163.0 on the codex-openlux-auto lane. **Auto-trust with zero user action works, with two independent variants proven.**

- **P1.1 confirmed.** Scratch-home `hooks.json` + `--dangerously-bypass-hook-trust` runs all hooks in unattended TUI mode: composer at ~0.7 s, zero keypresses, no trust modal, full turn cycle (`SessionStart` 64 ms after the first prompt's Enter, `UserPromptSubmit` +44 ms, `Stop`, `SessionEnd` on `/quit`). One correction to the proposition's wording: at 0.163.0 `SessionStart` is queued at session creation but dispatched only when the first turn begins (`core/src/session/turn.rs:340`), so "arrives within the startup grace" means "fires at first-prompt time", not before it. Evidence: [S0 gate (openlux)](../evidences/2026-10-20-s0-gate-smoke-openlux.md).
- **P1.2 confirmed, and the hash is proven load-bearing.** Pre-writing `[hooks.state."<key>".trusted_hash]` computed by the harness's `hash_hook.py` into the scratch home's `config.toml` runs all hooks with NO bypass flag and no modal. Perturbing one command (same path, stale hash) paints `N hooks are new or changed.` and no event from the perturbed generation runs. Empirical validation: Codex's own trust-all write in the S2 interactive arm produced 12 `trusted_hash` entries, **12/12 byte-identical** to `hash_hook.py --emit-state` output (verified independently after the run). The two computed entries Codex did not write are exactly `pre_model_request`/`post_model_request`, which 0.163.0 excludes from the trust-review set. One production note: Codex's trust-all writes state into the **active profile file** (`openlux-auto.config.toml`), not `config.toml`; houmao's pre-trust should keep targeting `config.toml` (which worked in T1) since launcher profile refreshes can clobber the profile file. Evidence: [T1](../evidences/2026-10-20-t1-pretrusted-hash.md), [S2](../evidences/2026-10-20-s2-trust-control-and-interactive.md).
- **P1.3 confirmed (failure mode documented).** Hooks present with neither bypass nor pre-trust: a **blocking** `Hooks need review` modal paints at startup, zero hook events fire, and the session waits for input forever — an unattended session hangs exactly as feared. The live modal at 0.163.0 starts its `›` marker on row 1 (`Review hooks`); trust-all is `Down, Enter`. After trust-all, hooks run immediately. Evidence: [S2 control + interactive](../evidences/2026-10-20-s2-trust-control-and-interactive.md).
- **P1.4 confirmed at the raw-launch level.** `-c hooks.<Event>=[...]` session-flags injection (28 args, no `hooks.json`) + bypass flag delivers the full turn cycle. Whether the managed launch path's caller-override canonicalization preserves `hooks.*` is source-supported (not an owned surface) but not live-tested through `houmao-mgr` — named leftover for the implementation change. Evidence: [T2](../evidences/2026-10-20-t2-session-flags.md).

Summary: both injection variants run hooks with zero user action in unattended mode. The campaign's E1 decision (see the [iteration 1 report](../reports/2026-10-20-iteration-1-merge-replay.md)) chooses **P1.2 — pre-written `[hooks.state."<key>".trusted_hash]` in the runtime-home `config.toml`** as primary for the managed path: it is least-privilege (no blanket dangerous flag; only the exact vetted commands run), the hash tool is empirically proven (12/12 against Codex's own write), and houmao already owns runtime-home synthesis so hash maintenance is automatic at generation time. **P1.1 (bypass flag) is the tested fallback**, and P1.4 (`-c`) remains an experimental surface pending managed-path live validation.

Additional findings carried to KQ-2: model identity on the openlux lane is `gpt-6.1-sol`; `PreModelRequest`/`PostModelRequest` were not observed firing in any arm (consistent with their exclusion from the 0.163.0 review set — availability verdict belongs to the payload catalog).

## Scope

Covers launch-time injection and trust only. Payload contents are KQ-2; delivery semantics are KQ-3. Evidence: `evidences/` links added as produced.
