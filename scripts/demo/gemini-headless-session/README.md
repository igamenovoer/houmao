# Gemini Headless Runtime Demo

This tutorial pack demonstrates a non-CAO Gemini session: build a brain home, start a `gemini_headless` runtime session, send one prompt, and verify that a non-empty response is returned.

## Prerequisites

- `pixi` is installed and working.
- Gemini CLI is installed and available on `PATH`.
- Credential profile exists under `$AGENT_DEF_DIR/brains/api-creds/gemini/personal-a-default/`.
  - This demo expects `files/oauth_creds.json` and `env/vars.env`.

## What It Does

1. Uses `build-brain` for tool `gemini` with local config + creds profile.
2. Starts a `gemini_headless` runtime session.
3. Sends one prompt from [`inputs/prompt.txt`](inputs/prompt.txt).
4. Verifies the generated report against [`expected_report/report.json`](expected_report/report.json).

## Run

```bash
scripts/demo/gemini-headless-session/run_demo.sh
```

Optional snapshot refresh:

```bash
scripts/demo/gemini-headless-session/run_demo.sh --snapshot-report
```

## Verify

- The script writes a runtime report under `tmp/demo_gemini_headless_*/report.json`.
- Verification is done by [`scripts/verify_report.py`](scripts/verify_report.py).
- The verifier enforces:
  - non-empty `response_text`,
  - `backend == "gemini_headless"`,
  - `tool == "gemini"`,
  - sanitized shape matches `expected_report/report.json`.

## SKIP Behavior

The demo exits `0` with a `SKIP:` message when:

- credentials are missing,
- credentials are invalid/unauthorized,
- connectivity to provider endpoints is unavailable.

Unexpected failures (for example invalid script assumptions or missing required binaries) exit non-zero.
