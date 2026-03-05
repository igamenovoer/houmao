## 1. Codex Runtime Bootstrap

- [x] 1.1 Add a runtime-owned Codex bootstrap helper that loads/patches runtime-home `config.toml` idempotently.
- [x] 1.2 Resolve launch-context trust target (repo root when discoverable, else workdir) and seed `[projects."<path>"] trust_level = "trusted"`.
- [x] 1.3 Apply policy-driven non-interactive Codex config edits (trust + required notice state always; `approval_policy` / `sandbox_mode` only if explicitly present in the Codex config profile; preserve unrelated user/profile settings).
- [x] 1.4 Invoke Codex bootstrap in both launch paths: `backend=codex_app_server` and Codex `backend=cao_rest`.

## 2. Shadow Status Contract Extension

- [x] 2.1 Extend shared shadow status typing/contracts to include `unknown` and runtime lifecycle `stalled` handling.
- [x] 2.2 Update Codex shadow parser classification to emit `unknown` for recognized-but-unclassifiable snapshots.
- [x] 2.3 Update Claude shadow parser classification to emit `unknown` for recognized-but-unclassifiable snapshots.

## 3. CAO Shadow Polling Policy

- [x] 3.1 Add runtime config plumbing for `runtime.cao.shadow.unknown_to_stalled_timeout_seconds` (default 30) and `runtime.cao.shadow.stalled_is_terminal` (default false).
- [x] 3.2 Implement unknown-duration tracking in CAO shadow readiness/completion loops and transition to `stalled` at configured threshold.
- [x] 3.3 Implement configurable stalled terminality behavior: immediate error when terminal, continued polling/recovery when non-terminal.
- [x] 3.4 Add metadata/anomaly diagnostics for unknown/stalled entry, elapsed duration, and stalled recovery (emit `stalled_entered` / `stalled_recovered` anomaly codes with phase + durations).

## 4. Tests

- [x] 4.1 Add/extend unit tests for Codex bootstrap config projection and trust seeding behavior.
- [x] 4.2 Add parser unit tests for `unknown` classification in Codex and Claude fixtures.
- [x] 4.3 Add CAO runtime tests for unknown->stalled transition, terminal stalled failure, and non-terminal stalled recovery.
- [x] 4.4 Ensure existing shadow-only no-cross-mode-fallback behavior remains covered after stalled-state additions.

## 5. Documentation

- [x] 5.1 Update `docs/reference/cao_shadow_parser_troubleshooting.md` with `unknown` vs `stalled` semantics, tuning knobs, and recovery guidance.
- [x] 5.2 Update `docs/reference/brain_launch_runtime.md` with Codex bootstrap behavior and new shadow stall policy configuration fields.
- [x] 5.3 Add operator troubleshooting examples showing stalled terminal vs non-terminal behavior and expected diagnostics.
