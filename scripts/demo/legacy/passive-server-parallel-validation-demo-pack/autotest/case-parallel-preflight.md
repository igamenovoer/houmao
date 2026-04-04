# `parallel-preflight`

Run the demo pack's fail-fast prerequisite checks without starting either authority.

## Steps

1. Run `autotest/run_autotest.sh --case parallel-preflight --demo-output-dir <path>`.
2. Confirm the command exits successfully before any server or agent startup begins.
3. Inspect `<path>/control/` and the autotest logs to confirm the pack recorded preflight output.

## Success Criteria

- The output confirms required executables, ports, fixtures, and credential material are available.
- No old `houmao-server`, passive server, or managed-agent session is started during this case.

