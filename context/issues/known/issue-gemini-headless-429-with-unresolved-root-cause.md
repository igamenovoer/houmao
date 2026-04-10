# Gemini Headless May Surface 429 While Root Cause Remains Unclear

## Status
Known issue as of 2026-04-09. Root cause is not yet determined.

## Symptom

- Gemini can answer normally in interactive TUI usage.
- A Houmao-managed Gemini headless run may report a `429` / rate-limit-style problem when launched inside a temp runtime under `tmp/<subdir>`.
- At least some of these reports may be confusing because Gemini can emit a transient `429` diagnostic to stderr and still complete the turn successfully.

## Confirmed Observations

### Environment checked on 2026-04-09

- Installed Gemini CLI version on this machine: `0.37.0`
- User home Gemini auth shape:
  - `~/.gemini/settings.json` exists
  - `~/.gemini/oauth_creds.json` exists
  - `~/.gemini/google_accounts.json` exists
  - `security.auth.selectedType = "oauth-personal"`
  - no `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT`, or `GOOGLE_CLOUD_LOCATION` were present in the current shell during the check

### Headless runs that succeeded during investigation

1. An isolated temp `GEMINI_CLI_HOME` built from the current user `~/.gemini` state succeeded in headless mode.
   Artifact:
   [`tmp/gemini-user-compare-0YSxiz/isolated.stream.jsonl`](/data1/huangzhe/code/houmao/tmp/gemini-user-compare-0YSxiz/isolated.stream.jsonl)

2. A minimal Houmao-like temp Gemini home with only projected `oauth_creds.json` plus `GOOGLE_GENAI_USE_GCA=true` also succeeded in headless mode.
   Artifact:
   [`tmp/gemini-managed-like-OPsGcf/run.stream.jsonl`](/data1/huangzhe/code/houmao/tmp/gemini-managed-like-OPsGcf/run.stream.jsonl)

These two checks show that fresh temp-home headless Gemini is not generically broken on this machine.

### Earlier local probe showing transient 429 with successful completion

An earlier repo-local probe from 2026-04-02 under Gemini CLI `0.36.0` captured a real upstream `429` on stderr:

- [`tmp/gemini-headless-check/artifacts/turn1.stderr`](/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn1.stderr)

That stderr includes:

- HTTP status `429`
- upstream status `RESOURCE_EXHAUSTED`
- detail `MODEL_CAPACITY_EXHAUSTED`
- model metadata indicating `gemini-3-flash-preview`

However, the same turn still completed successfully:

- [`tmp/gemini-headless-check/artifacts/turn1.stream.jsonl`](/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn1.stream.jsonl)

That successful output means a transient provider-side quota or capacity event can appear in stderr even when the final turn result is successful.

### Houmao behavior that can amplify confusion

Houmao currently mirrors provider stderr lines into canonical diagnostic events:

- [`src/houmao/agents/realm_controller/backends/headless_bridge.py`](/data1/huangzhe/code/houmao/src/houmao/agents/realm_controller/backends/headless_bridge.py)
- [`src/houmao/agents/realm_controller/backends/headless_output.py`](/data1/huangzhe/code/houmao/src/houmao/agents/realm_controller/backends/headless_output.py)

This means a Gemini retry or fallback warning written to stderr can be surfaced to the operator even if the final provider result is success.

## Current Guesses

These are hypotheses only, not confirmed root causes.

### Hypothesis 1: transient Gemini retry diagnostics are being mistaken for final failure

Gemini appears able to emit stderr warnings for transient `429` / capacity issues and still recover within the same turn. Houmao may currently surface that warning prominently enough that the run looks failed or "weird" even when the final `stream-json` result is successful.

### Hypothesis 2: some specific Houmao-managed runs still differ from the successful minimal probes

The exact failing managed runtime may still differ in one of these ways:

- projected `.gemini/settings.json`
- working directory / project identity
- inherited env vars
- proxy behavior
- model-routing state
- persisted session or temp-home contents

No exact failing managed session directory from the user's reported `tmp/<subdir>` has been inspected yet, so this remains unresolved.

### Hypothesis 3: interactive TUI and managed headless runs may land on different effective state

Interactive Gemini can reuse the user's normal home, session history, and project-scoped state. A managed Houmao headless run uses an isolated projected temp home. Even if both are OAuth-backed, they may not hit identical routing, cached state, or fallback behavior.

## Not Yet Determined

- Whether the user-reported Houmao run actually ended with a nonzero exit code or only surfaced a stderr warning.
- Whether the exact failing `tmp/<subdir>` contains a real provider failure in `stderr.log` plus `exitcode`, or a successful `stdout.jsonl` result with only transient diagnostics.
- Whether Gemini CLI `0.37.0` changed any relevant fallback or retry behavior relative to the older `0.36.0` local probe.

## Next Useful Evidence

To determine the real root cause, inspect one exact failing managed runtime directory and compare:

- `stdout.jsonl`
- `stderr.log`
- `exitcode`
- projected `.gemini/settings.json`
- manifest / launch env records

Until that evidence is inspected, this issue should be treated as unresolved and only partially characterized.
