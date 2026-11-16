# DSH Qualification

This opt-in runner uses the maintained fixture helper and an explicitly chosen external credential file. It never loads ambient API auth or vendor-login JSON. All model calls and generated homes remain in private external fixture runs; the report contains build/model/protocol metadata and outcomes only.

First prepare an isolated qualified executable with [the DSH development helper](../../../tools/dsh/README.md). Populate an external env file using the variable names in [the generic descriptors](../../../tests/fixtures/agent-launch/README.md), including exact model context, maximum output tokens, and DSH reasoning support. No self-hosted service is needed for `cloud-api`.

## Headless ACP

```bash
pixi run python scripts/qualification/dsh/qualify.py --check-only \
  --case cloud-api --env-file /external/selected-deepseek.env
pixi run python scripts/qualification/dsh/qualify.py \
  --case cloud-api --env-file /external/selected-deepseek.env \
  --executable /selected/qualified-runtime/node_modules/.bin/dsh \
  --surface manager --output /external/dsh-qualification/report.json
```

## Controlled Web Browser and API

The native Web conformance and browser suites use the actual selected executable, synthetic credentials, and controlled loopback Messages models. They make no paid provider requests and need no desktop display. Bun resolves the installed Playwright API; the browser helper reuses an installed Chromium bundle. Set `HOUMAO_PLAYWRIGHT_CHROMIUM_EXECUTABLE` when an explicit installed browser is required. The helper does not download a browser.

```bash
env -u TMUX -u TMUX_PANE \
  HOUMAO_DSH_EXECUTABLE=/selected/qualified-runtime/node_modules/.bin/dsh \
  pixi run python -m pytest -q tests/integration/agents/dsh/web/
```

The test browser signs in using a user-private descriptor outside the checkout, verifies the clean origin, expands native sidebar groups, and selects the exact published native session. A fresh native profile may show its preview notice; the test acknowledges that notice without supplying a provider credential through the browser. The browser and program use independent native peers. Tests navigate through the real native UI; production observation never reads the DOM.

Controlled checks cover shared history and streamed progress, browser-local drafts, API/browser prompt alternation, native navigation without programmatic retargeting, browser/API interruption, retained queued human input, and human questions under deliberate `as_is` posture. Test-only native preparation gates establish both admission race orders. Native conformance separately exercises maintenance, lost receipt reconciliation, authorization revocation, replacement, and pre-activation recovery. Passing these checks does not imply a paid-provider result.

Private browser error diagnostics, native logs, cookies, startup tokens, and transcripts stay in the external test run. The bridge returns only approved metadata and never prints raw Playwright errors or signed navigation URLs. No screenshots are captured by the maintained runner. See the [Web compatibility reference](../../../docs/reference/run-phase/dsh-web.md) and [scenario map](../../../docs/reference/run-phase/dsh-web-acceptance.md) for executed evidence and remaining acceptance gates.

## Live Web Qualification

The Web runner uses a managed fixture and an actual Bun/Chromium browser with independent API authorization. Select the external env file explicitly. Offline mode validates route/model metadata without starting a host or contacting the provider:

```bash
pixi run python scripts/qualification/dsh/qualify_web.py --check-only \
  --case cloud-api --env-file /external/selected-deepseek.env
pixi run python scripts/qualification/dsh/qualify_web.py \
  --case cloud-api --env-file /external/selected-deepseek.env \
  --executable /selected/qualified-runtime/node_modules/.bin/dsh \
  --output /external/dsh-qualification/web-report.json
```

The live command sends billable prompts. It verifies API and browser shell-tool file oracles, exact shared-session continuation, completed human-origin consumption, interruption of the captured human turn, explicit exact host relaunch, and two isolated homes. The report records the real browser/build/model/protocol and separates each check. Any failure retains private evidence and triggers owned cleanup. Reconnection, lookup, timeout, and relaunch never resend an earlier prompt. Use `--case self-hosted` only with a deliberately configured compatible deployment/model; a cloud result does not qualify that lane.

For a manually prepared Web fixture, `fixture.py browser-connection --run-dir /external/prepared-run` writes a user-private connection descriptor and returns its path. Only a deliberate local browser consumer should read it. Its token and resulting browser storage stay private; public fixture summaries and `report.json` contain the clean origin and exact session identity. Private `run.json` retains credential-file references for verified control. The root token exchange signs in, then the native sidebar selects that session. The API continues to use separate `interactions=none` credentials.

## Live Headless Qualification Limits

The `qualify.py` live invocation sends billable prompts. It checks a native shell-tool file oracle, completion, exact native continuation in a later worker, native cancellation, public managed journal accounting, and two independent homes/native sessions. It records actual source/executable/package identities separately from the ACP placeholder version. Each failure leaves private evidence for inspection and triggers scoped cleanup; the runner never automatically resends a failed prompt.

`--surface raw` exercises the native ACP driver without tmux but reports managed usage-route qualification as not run. `--surface passive-server` requires an explicitly selected `--passive-url`; that separately owned server must use external runtime/registry roots and its own explicit isolated tmux server. The manager lane uses the fixture's private per-run `tmux -L` server and PATH shim. No command restarts or kills the shared localhost/default server.

For self-hosted qualification, invoke the runner separately with `--case self-hosted`, its explicitly chosen env file, and a compatible model other than Qwen3.8. If that deployment or model is unavailable, preserve the report's not-run reason. Running without `--env-file` produces a not-run report and performs no model request. `--check-only` validates configuration without qualifying live credentials or outcomes. Headless results never qualify the successor interactive Web lane or close the combined issue #74 scope.
