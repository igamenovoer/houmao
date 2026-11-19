# Tasks

## 1. Select and Prepare the Native DSH CLI

- [x] 1.1 Register `dsh_headless` in the shared resolver, runtime factory, DSH launch policy, and tool-parameter backend validation. Assert the normal project and passive headless launches select `--profile headless --json` and reject ACP-only backend requests.
- [x] 1.2 Read the selected private native home, role, credentials, model, reasoning, and permission inputs at their documented boundaries. Test materialized home edits, native precedence, `as_is`, and a supported CLI projection or explicit rejection for each requested MCP form.
- [x] 1.3 Update DSH launch documentation and raw/managed fixture preparation. Compare emitted arguments for self-hosted Qwen 3.8 and a controlled cloud configuration with explicit model and private auth inputs.

## 2. Run One Fenced Attempt per Prompt

- [x] 2.1 Drive the native CLI using private stdin inside the managed headless envelope and implement exact `--session-id` continuation. Verify two completed prompts have different worker identities and the same native conversation, and an unavailable saved ID cannot create a replacement.
- [x] 2.2 Reuse the shared owner reservation and bind its generation, attempt and revocable bridge permission at native input. Exercise cancellation or caller loss between worker start and native `followup`. Verify the companion prevents late or duplicate delivery and records admission only after the native mutation.
- [x] 2.3 Capture NDJSON and diagnostics privately, normalize session and outcome events, and reconcile journal continuity, flush and process exit. Cover malformed/partial streams, native `error`, limit outcomes, secret redaction, separately billed retries, and missing usage.
- [x] 2.4 Implement bounded interruption and process-tree cleanup using the captured attempt. Test controller timeout, signal escalation, partial artifacts, and a stale interrupt racing a replacement worker. Document the guarantees provided by native outcomes and owned-process observation.

## 3. Qualify the Public Headless Flow

- [x] 3.1 Update the passive launch allowlist, turn recovery, event projection, and raw stdout access. Restart the passive controller during an admitted turn and verify that status recovery never executes the prompt again.
- [x] 3.2 Use the fixture helper with the selected DSH build and self-hosted `Qwen/Qwen3.8-27B-FP8` to prove fresh launch, exact continuation, interruption, stop/relaunch, gateway submission, and usage continuity. Keep credentials and run artifacts outside the checkout. Record the build, mode, backend, and any unavailable prerequisite under `logs/`.
- [x] 3.3 Run the DSH unit and integration suites under Pixi on an isolated tmux server. Check the maintained operator example selects native one-shot execution and the earlier ACP smoke is identified as independent evidence.

## Workflow Follow-up

- At spec synchronization, update the existing `dsh-headless-control` purpose sentence to name the qualified native one-shot CLI. Confirm the prior per-turn ACP description is no longer published as headless behavior.
