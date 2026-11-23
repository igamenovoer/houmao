# Tasks

## 1. Packaged Minimums and Preflight

- [x] 1.1 Convert the Kimi ACP, Kimi Web, and Codex app-server registry selectors to inclusive minimums. Test every packaged DSH, Kimi, Claude, and Codex strategy at its floor, above its floor, and below its floor.
- [x] 1.2 Use the packaged minimum and shared version matching in DSH, Kimi ACP, Kimi Web, and Codex app-server preflight. Exercise project launch, direct runtime startup, and explicit relaunch in tests. Verify `as_is` launch and the strategy override cannot bypass a native minimum, and that below-minimum validation precedes force takeover.
- [x] 1.3 Verify version extraction and comparison with the CLI output forms used by these tools. Add regressions for suffix preservation, DSH RC ordering, malformed output, and the release/RC channel policy. Check failure messages identify the affected tool, mode, and requirement.
- [x] 1.4 Document the per-mode minimums and release channels in the launch-policy reference. Cross-check the table against all four packaged registries, and clarify the Kimi mode split and DSH inspect requirement in the relevant setup and tooling guides.

## 2. Native Startup

- [x] 2.1 Apply the Kimi Web minimum when validating launch metadata. Verify a newer launch reaches native listener and session validation, and that incompatible API or owner identity fails without readiness. Update the Kimi Web and fixture guides.
- [x] 2.2 Validate Kimi ACP protocol, capabilities, and the reported version against the selected executable. Verify a newer peer binds the expected session and records its actual version, and that incompatible protocol, capability, or identity prevents readiness. Update the Kimi ACP and fixture guides.
- [x] 2.3 Validate the Codex app-server peer against the selected executable and private home, and record its actual version. Verify an eligible newer peer binds the expected thread and that a malformed handshake or mismatched home or version fails with an actionable service error. Update the Codex service and fixture guides.
- [x] 2.4 Cross-check the backend overview and affected operator examples against the minimums and label build-specific qualification evidence.

## 3. Integration Verification

- [x] 3.1 Run the maintained agent fixture with an explicitly selected model and executable for Kimi Web 2.7.2 and available newer Kimi ACP and Codex app-server builds. Verify launch, one managed prompt, and stop. Record exact build and outcome, including any native compatibility failure or unavailable live test.
- [x] 3.2 Run the focused launch-policy, runtime, and manager suites with Pixi. Confirm startup does not infer usage or refresh qualification for a newer build. Record the commands and results.
