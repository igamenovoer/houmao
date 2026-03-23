# Issue 005: Baseline Invalidation Without Recovery + Four-Root Environmental Coupling

## Priority
P2 — Long-running sessions drift; every new environment rediscovers the same cascade.

## Status
Known.

## Review Reference
Code review sections: 2.5, 2.7, 4.3.1 (Rx re-baseline), 4.7 (four-root model)

## Summary

Two related problems about the runtime lifecycle operating against an underspecified environment model:

### A. Baseline position invalidation without recovery (2.5)

The baseline position is captured as a character offset into normalized text. When the terminal buffer cycles (tmux scrollback limit reached), `len(clean_output) < baseline_pos`. The parser records `baseline_invalidated=true` as an anomaly but has no recovery strategy — it continues parsing with the invalid baseline, which can cause:
- Response markers from the current turn to be counted as pre-baseline (ignored)
- Old markers from a different turn to be counted as current

### B. Four-root environmental coupling (2.7)

The shadow parser's reliability depends on four environmental root classes all being correct:

1. **Source snapshot** — the code
2. **Operator-local credentials** — API keys, auth tokens
3. **Tool-owned runtime state** — home dirs, cached configs, trust decisions
4. **Launched project workdir** — where the tool is pointed at

In the main checkout these overlap implicitly. In a clean worktree, any missing root cascades down to a confusing parser failure:

```
Missing credentials → preflight fail → (workaround) →
CAO workdir-outside-home → session start fail → (workaround) →
Tool shows setup prompts → parser sees noise → parse fail
```

The parser appears to fail on TUI parsing, but the root cause is environmental.

## Root Cause

A. Character-offset baselines assume a monotonically growing text buffer. Terminal emulators don't guarantee this.

B. The run model doesn't explicitly model the four roots as separate, required inputs. Ambient host state silently satisfies implicit contracts.

## Affected Code

- `src/houmao/agents/realm_controller/backends/claude_code_shadow.py` — `parse_snapshot()` (line 330), `capture_baseline_pos()`
- `src/houmao/agents/realm_controller/backends/cao_rest.py` — `_capture_shadow_baseline()`, `_wait_for_shadow_completion()`
- Run planner / launch plan assembly

## Fix Direction

### A. Rx `scan()` re-baseline (from issue-002's Rx pipeline)

```python
ops.scan(lambda acc, snapshot: _maybe_rebaseline(acc, snapshot), seed=initial_state)
```

The `scan` accumulator detects baseline invalidation, captures a new baseline from the current snapshot, and emits an anomaly — within the stream, no external mutable state.

### B. Explicit run-root model in the run planner

The run plan should explicitly model: `source_root`, `project_workdir`, `runtime_root`, `tool_state_root`, `external_prereqs`. No step should silently assume one root can stand in for another.

This is a broader change that extends beyond the shadow parser. The capability probe (issue-004) addresses the parser-boundary manifestation. The full run-root model is a run-planner concern tracked in the existing HTT issue.

## Connections

- Baseline recovery is naturally handled inside the Rx pipeline from issue-002
- Four-root model connects to existing HTT issue: `context/issues/known/issue-real-agent-htt-worktree-runs-mix-snapshot-and-host-state.md`
- Capability probe (issue-004) addresses the parser-layer manifestation of missing roots
