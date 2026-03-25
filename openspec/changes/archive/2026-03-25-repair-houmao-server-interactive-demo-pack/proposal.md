## Why

`houmao-server-interactive-full-pipeline-demo` still encodes assumptions from an older pair boundary. Since `houmao-mgr launch --headless` now means native headless launch and the public managed-agent stop surface has moved to `/houmao/agents/{agent_ref}/stop`, the demo can miss its own delegated artifacts, depend on private launch helpers, and teach an outdated stop flow.

## What Changes

- Repair demo startup so detached TUI launch uses the supported public compatibility path instead of a private `houmao-mgr` helper or the top-level native-headless launch meaning.
- Require pair install and detached launch subprocesses to run with the demo-owned runtime, registry, jobs, and home roots so delegated artifacts stay inside the run root.
- Change demo stop from raw CAO session deletion to the managed-agent stop route on the persisted `houmao-server` authority.
- Refresh demo README, shell wrappers, and tests so they describe and verify the current `houmao-server + houmao-mgr` boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-server-interactive-full-pipeline-demo`: update the demo-pack requirements so startup uses the supported detached TUI pair surface, delegated artifacts stay demo-owned, and stop uses the managed-agent lifecycle route.

## Impact

- Affected code: `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/*` and `scripts/demo/houmao-server-interactive-full-pipeline-demo/*`
- Affected tests: `tests/unit/demo/test_houmao_server_interactive_full_pipeline_demo.py`
- Affected docs: demo README plus any pair/reference docs that still describe the outdated startup or stop flow
