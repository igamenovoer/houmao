## 1. Runtime Completion Gating

- [x] 1.1 Thread a mailbox-aware completion contract through the CAO `shadow_only` prompt/mailbox path without changing the parser-owned `business_state` and `input_mode` model.
- [x] 1.2 Keep polling post-submit shadow text for the active mailbox request after provisional shadow completion until one sentinel-delimited mailbox result is available or the existing bounded failure policy ends the turn.
- [x] 1.3 Preserve explicit mailbox parse errors for malformed or duplicate sentinel payloads while eliminating premature missing-sentinel failure at transient submit-ready rebounds.

## 2. Regression Coverage

- [x] 2.1 Add unit coverage for delayed mailbox sentinel arrival after the surface returns to submit-ready with post-submit progress evidence.
- [x] 2.2 Add runtime/integration coverage that exercises the mailbox sender path and proves the command waits for sentinel output instead of failing early when the agent is still working.

## 3. Verification

- [x] 3.1 Run the targeted runtime/mailbox test suites and any touched lint checks needed to verify the new completion behavior.
