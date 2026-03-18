# Issue 004: Fresh-Environment TUI Noise — No Capability Probe, No Operator-Block Recovery

## Priority
P1 — Late, confusing failures in clean environments, HTT worktrees, and CI.

## Status
Known.

## Review Reference
Code review sections: 2.6, 3.4, 3.5, 4.7

## Summary

The shadow parser was calibrated to the steady-state TUI of an already-configured tool. In fresh environments (disposable worktree, clean CI runner, new machine), CLI tools emit first-run content that the parser either misclassifies or can't recover from:

- **Installer/onboarding prompts** — "Complete setup", "Sign in", "Continue in browser" before any prompt appears. Detected as `awaiting_operator` but the readiness gate raises `BackendExecutionError` with no recovery path.
- **Trust/folder prompts** — "Allow Claude to work in this folder?" on first entry. Detected as `awaiting_operator` / `trust_prompt`, but automation has no mechanism to answer it.
- **Banner messages** — Fresh installs emit extra banner lines, update notices, or migration messages that shift what `_active_prompt_payload()` considers the "last non-empty line."

When the parser detects `awaiting_operator`, the `_TurnMonitor` transitions to `blocked_operator` and the turn engine raises `BackendExecutionError`. There is no mechanism to auto-answer, dismiss, or retry-after-intervention. This makes `awaiting_operator` a terminal state in automation, even for trivially resolvable blocks.

## Root Cause

1. No preflight step verifies whether the tool requires login/setup, has trusted the project directory, or matches a known parser preset.
2. `awaiting_operator` is treated as immediately terminal with no intervention window.
3. The system implicitly depends on ambient host state (tool already set up, already trusted) — invisible in the main checkout, immediately breaking in clean environments.

## Affected Code

- `src/houmao/agents/realm_controller/backends/cao_rest.py` — `_wait_for_shadow_ready_status()`, `_wait_for_shadow_completion()` (the `blocked_operator` → raise path)
- `src/houmao/agents/realm_controller/backends/claude_code_shadow.py` — `_SETUP_BLOCK_RE`, `_TRUST_PROMPT_RE`, `_classify_surface_axes()`

## Fix Direction

### A. Pre-turn capability probe (4.7.1)

Before the first readiness wait, run a lightweight probe:

1. Capture one snapshot immediately after session creation.
2. Parse for setup block, trust prompt, disconnected signals.
3. Setup/login block → fail fast with actionable error: "Tool requires interactive setup."
4. Trust prompt → auto-send trust confirmation (if policy allows) or fail fast with specific message.
5. Idle prompt → proceed.
6. Unknown → proceed with warning.

This converts late "timed out waiting for shadow readiness" into early "the tool isn't set up for automated use."

With Rx (from issue-002), the probe becomes the head of the readiness pipeline:

```python
ops.do_action(lambda s: _raise_if_setup_block(s)),
ops.do_action(lambda s: _auto_trust_if_policy(s)),
```

### B. Operator-block intervention window (4.7.2)

Instead of treating `blocked_operator` as immediately terminal:

1. Emit structured event: `{"kind": "operator_intervention_needed", "block_type": "trust_prompt", ...}`
2. Keep polling for `operator_block_intervention_timeout_seconds` (configurable, default 0 for current behavior).
3. If block clears within window → resume.
4. If timeout → raise as today.

## Connections

- Depends on issue-002 (Rx pipelines provide the readiness pipeline where the probe is integrated)
- Amplifies issue-003 (startup noise adds extra signals to the tail window)
- Addresses HTT worktree cascade layer 3 (see issue-005)
- Related to existing HTT issue: `context/issues/known/issue-real-agent-htt-worktree-runs-mix-snapshot-and-host-state.md`
