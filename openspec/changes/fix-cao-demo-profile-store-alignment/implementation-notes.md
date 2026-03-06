# Implementation Notes

## Validation Commands

### Shell syntax checks

```bash
bash -n scripts/demo/cao-codex-session/run_demo.sh \
  scripts/demo/cao-claude-tmp-write/run_demo.sh \
  scripts/demo/cao-claude-esc-interrupt/run_demo.sh
```

Result: pass (exit 0).

### Sequential targeted demo runs (single-port local CAO)

```bash
scripts/demo/cao-codex-session/run_demo.sh
scripts/demo/cao-claude-tmp-write/run_demo.sh
scripts/demo/cao-claude-esc-interrupt/run_demo.sh
```

Results:

- `cao-codex-session`: pass (`verification passed`, demo complete).
- `cao-claude-tmp-write`: fail in this development workspace due to intentional dirty-worktree guard (`git diff --name-only is not empty after demo`).
- `cao-claude-esc-interrupt`: pass (`verification passed`, demo complete).

### Skip taxonomy verification for profile-store mismatch

Ran each demo with deliberate profile-store mismatch:

```bash
CAO_PROFILE_STORE="/tmp/cao-profile-store-mismatch-$$" scripts/demo/cao-codex-session/run_demo.sh
CAO_PROFILE_STORE="/tmp/cao-profile-store-mismatch-$$" scripts/demo/cao-claude-tmp-write/run_demo.sh
CAO_PROFILE_STORE="/tmp/cao-profile-store-mismatch-$$" scripts/demo/cao-claude-esc-interrupt/run_demo.sh
```

Result for all three: `SKIP: CAO profile store mismatch` (from start-session failure classification), confirming mismatch is no longer labeled as `missing credentials`.
