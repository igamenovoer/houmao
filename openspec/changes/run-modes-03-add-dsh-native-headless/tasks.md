# Tasks

## 1. Select and Prepare the Native DSH CLI

- [ ] 1.1 Register `dsh_headless` in the shared resolver, runtime factory, DSH launch policy, and tool-parameter backend validation. Assert the normal project and passive headless launches select `--profile headless --json` and reject ACP-only backend requests.
- [ ] 1.2 Read the selected private native home, role, credentials, model, reasoning, and permission inputs at their documented boundaries. Test materialized home edits, native precedence, `as_is`, and a supported CLI projection or explicit rejection for each requested MCP form.
- [ ] 1.3 Update DSH launch documentation and raw/managed fixture preparation. Compare emitted arguments for one self-hosted and one cloud configuration with explicit model and private auth inputs.

## 2. Run One Fenced Attempt per Prompt

- [ ] 2.1 Drive the native CLI using private stdin inside the managed headless envelope and implement exact `--session-id` continuation. Verify two completed prompts have different worker identities and the same native conversation, and an unavailable saved ID cannot create a replacement.
- [ ] 2.2 Bind managed generation, attempt and revocable dispatch permission at native input. Exercise cancellation or caller loss between worker start and native `followup`; verify the companion or equivalent native evidence prevents late or duplicate delivery.
- [ ] 2.3 Capture NDJSON and diagnostics privately, normalize session and outcome events, and reconcile journal continuity, flush and process exit. Cover malformed/partial streams, native `error`, limit outcomes, secret redaction, separately billed retries, and missing usage.
- [ ] 2.4 Implement bounded interruption and process-tree cleanup using the captured attempt. Test controller timeout, signal escalation, partial artifacts, and a stale interrupt racing a replacement worker. Document the guarantees provided by native outcomes and owned-process observation.

## 3. Qualify the Public Headless Flow

- [ ] 3.1 Update the passive launch allowlist, turn recovery, event projection, and raw stdout access. Restart the passive controller during an admitted turn and verify that status recovery never executes the prompt again.
- [ ] 3.2 Use the fixture helper with an explicitly selected native build, case, and model to prove fresh launch, exact continuation, interruption, stop/relaunch, gateway submission, and usage continuity. Keep credentials and run artifacts outside the checkout; record actual build, mode, backend, and any unavailable prerequisite.
- [ ] 3.3 Run the DSH unit and integration suites under Pixi on an isolated tmux server. Check the maintained operator example selects native one-shot execution and the earlier ACP smoke is identified as independent evidence.

## Workflow Follow-up

- At spec synchronization, update the existing `dsh-headless-control` purpose sentence to name the qualified native one-shot CLI. Confirm the prior per-turn ACP description is no longer published as headless behavior.
