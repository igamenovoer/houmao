## Why

Launch-profile memo seed policies currently describe `replace` as replacing both `houmao-memo.md` and the contained `pages/` tree, even when the operator supplied a memo-only seed through `--memo-seed-text` or `--memo-seed-file`. That behavior is surprising because the seed source shape tells users which managed-memory component they are editing, and memo-only edits should not clear unrelated page state.

## What Changes

- Scope memo seed policy checks and mutations to the managed-memory components represented by the stored seed source.
- Treat memo text and memo file seeds as touching only `houmao-memo.md`.
- Treat directory seeds as touching `houmao-memo.md` only when `houmao-memo.md` is present, and touching pages only when `pages/` is present.
- Preserve omitted managed-memory components for all policies, including `replace` and `fail-if-nonempty`.
- Document the difference between removing a stored seed with `--clear-memo-seed` and storing an intentional empty memo seed with `--memo-seed-text '' --memo-seed-policy replace`.
- No new CLI flags are introduced.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `brain-launch-runtime`: memo seed application policies become component-scoped instead of whole-memory-scoped.
- `agent-memory-freeform-memo`: memo-only seeds must not inspect, clear, or rewrite memory pages.
- `agent-memory-pages`: page-only seeds must not inspect or rewrite `houmao-memo.md`, and page replacement applies only when `pages/` is represented by the seed.
- `houmao-mgr-agents-launch`: explicit launch-profile-backed launches must report and apply memo seed results using the scoped policy semantics.
- `houmao-mgr-project-easy-cli`: easy profile-backed launches must report and apply memo seed results using the scoped policy semantics.
- `docs-launch-profiles-guide`: the launch-profiles guide must explain component-scoped policy behavior.
- `docs-cli-reference`: the CLI reference must avoid implying that memo-only seed replacement clears pages.
- `houmao-memory-mgr-skill`: the packaged memory skill must guide agents to use memo seed policies with component-scoped semantics.

## Impact

- Runtime memo seed application logic in `src/houmao/agents/launch_profile_memo_seeds.py`.
- Managed-memory helper behavior only insofar as existing memo/page read, write, and clear helpers are composed differently.
- Launch completion payloads may continue using the current `memo_seed` result shape, but counts and `memo_written` should reflect only the components touched by the seed.
- Unit tests for memo seed application and project/easy launch profile flows.
- Documentation in `docs/getting-started/launch-profiles.md`, `docs/reference/cli/houmao-mgr.md`, and packaged system-skill guidance for memory/profile memo seed management.
