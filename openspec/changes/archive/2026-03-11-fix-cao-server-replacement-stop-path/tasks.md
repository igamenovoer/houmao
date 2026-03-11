## 1. Launcher Stop Hardening

- [x] 1.1 Ensure launcher stop-result persistence creates the `launcher_result.json` parent directory before writing structured output from a fresh runtime root.
- [x] 1.2 Add launcher unit coverage proving `stop` returns structured `already_stopped` output when the artifact directory does not yet exist.

## 2. Demo Replacement Flow

- [x] 2.1 Update the interactive demo's known-config CAO replacement loop so one malformed or unusable launcher-stop result does not abort verified replacement while later known configs remain.
- [x] 2.2 Preserve explicit failure behavior when all known configs are exhausted or the fixed loopback occupant can no longer be safely treated as the verified local `cao-server`.
- [x] 2.3 Add unit coverage for the fresh-config-plus-older-owner replacement case and for the exhausted-known-config failure case.

## 3. Regression Validation

- [x] 3.1 Extend integration or wrapper-level demo coverage to exercise startup against an already-healthy fixed-port `cao-server`.
- [x] 3.2 Re-run the targeted launcher and interactive-demo test suites and confirm the occupied-`127.0.0.1:9889` startup path succeeds without manual cleanup.
