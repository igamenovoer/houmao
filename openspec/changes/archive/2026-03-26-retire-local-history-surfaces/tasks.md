## 1. Retire native local history surfaces

- [x] 1.1 Remove `houmao-mgr agents history` from the native CLI tree and help output.
- [x] 1.2 Delete the local managed-agent history wrapper code that exists only to serve the retired native CLI command, while leaving headless turn inspection commands intact.
- [x] 1.3 Update any native CLI docs/help references so supported inspection guidance points to `state`, `show`, gateway TUI state, or `agents turn ...` instead of generic managed-agent history.

## 2. Narrow runtime-owned local gateway tracking expectations

- [x] 2.1 Remove repo-owned local/serverless workflow reliance on `GET /v1/control/tui/history` for runtime-owned `local_interactive` sessions.
- [x] 2.2 Keep gateway-owned local tracking centered on `GET /v1/control/tui/state` plus explicit prompt-note evidence for runtime-owned `local_interactive`.
- [x] 2.3 Preserve compatibility plumbing still needed by the integrated CAO/server path without modifying that module in this change.

## 3. Validation and cleanup

- [x] 3.1 Update CLI shape and gateway tests so they no longer expect `houmao-mgr agents history` or local workflow reliance on gateway TUI history.
- [x] 3.2 Update workflow notes and reference docs that currently teach local/serverless history inspection.
- [x] 3.3 Verify the change remains apply-ready and explicitly document the remaining compatibility-only history boundary for future server-inclusive cleanup.

## Compatibility Boundary

- Shared gateway and server-facing history routes remain in place for integrated `houmao-server` and CAO compatibility consumers.
- Repo-owned local/serverless docs, tests, and workflow guidance now treat those history routes as compatibility-only and point operators to gateway-owned current state, explicit prompt-note evidence, `houmao-mgr agents state`, `houmao-mgr agents show`, or `houmao-mgr agents turn ...` instead.
