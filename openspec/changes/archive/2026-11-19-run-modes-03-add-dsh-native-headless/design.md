# Design

## Context

DSH's native headless profile reads a task, projects JSON events, waits for the root and descendant work to settle, flushes the session, and exits. The prior DSH adapter uses a fresh ACP connection for each turn. Changes 01 and 02 leave that ACP backend unqualified for new launches. They provide a shared owner reservation keyed by the current manifest path and registry generation. [Native one-shot implementation](../../../extern/orphan/deepseek-harness/packages/bundle/headless/src/index.ts), [owner reservation](../../../src/houmao/agents/realm_controller/owner_admission.py), and [RC2 ACP driver](../../../src/houmao/agents/realm_controller/backends/dsh_acp_driver.py).

## Goals / Non-Goals

Reuse Houmao's managed headless turn envelope, existing identity and usage journals, native role and home composition, and authenticated access. Bind the lifetime of one native headless process to one accepted prompt. Persistent ACP belongs to 04.

## Decisions

### Start a Native CLI Worker for Each Prompt

Register `dsh_headless` in the resolver, runtime, launch policy, tool-parameter checks, passive headless launch API, and fixture helper. Run the qualified executable with `--profile headless --json` and pass the task through private stdin. Omit `--session-id` for an explicit new conversation. For continuation, pass only the saved exact ID and original workspace. Honor DSH's preset, subagent, occupied-session and cwd validation. A saved ACP conversation may be incompatible. Never implicitly adopt it.

### Fence Between Process Startup and Native Input

Use the request identity assigned by change 02 as the attempt identity across manager, authenticated gateway, and passive launch paths. Bind the bridge's revocable, payload-free permission to the saved owner generation and its caller's process birth. The private companion checks that permission synchronously just before the native root's initial user `followup`, then records native inbox admission separately. Compare the companion's attempt, native session, and process with the envelope before publishing handoff. The qualified build must expose both the pre-mutation guard and the post-mutation receipt. A PID, accepted stdin, and JSON `session` line each prove only their own stage. If the fence or identity is unavailable, refuse the operation without sending input. [Managed companion](../../../src/houmao/agents/assets/dsh/managed-companion.mjs) and [bridge permission](../../../src/houmao/agents/realm_controller/backends/dispatch_control.py).

### Reconcile Events, Exit, and Journal

Capture raw NDJSON and stderr in private artifacts, bound surfaced diagnostics, and map events into the existing normalized stream. Match `sessionId` to the attempt. Combine native `final.reason`, exit status and flush evidence before setting a terminal outcome. Preserve native errors and partial output when the stream ends early. Reuse change 02's PID birth check and pinned signal path for the captured worker. Reconcile cleanup of the owned tree separately. Use the existing journal binding, source offsets and native attempt identities for usage, including retries and copied history. [JSON projection](../../../extern/orphan/deepseek-harness/packages/bundle/headless/src/json-stream.ts) and [DSH usage adapter](../../../src/houmao/agents/realm_controller/usage_adapters/dsh.py).

### Validate CLI Inputs on Their Own Terms

Keep the selected executable, private `DSH_HOME`, current materialized role, model, endpoint, credentials, native permission preset, and request overrides. Classify each MCP and skill input by its native read boundary. ACP `mcpServers` previously carried declarations during session binding. Prove an equivalent CLI-supported projection or explicitly reject the declaration in preflight. Ordinary prompts and observation leave materialized files intact. [DSH native configuration](../../../src/houmao/agents/dsh_configuration.py).

## Risks / Trade-offs

- A native error, cancelled process, or journal reset could look like success. Test malformed JSON, error without `final`, non-completion reasons, abnormal exit after output, interrupted descendants, and damaged journal continuity.
- A CLI launch can start while a stale client still holds dispatch permission. Exercise revocation immediately before native input and verify both the journal and managed receipt.

## Migration Plan

Enable the distinct `dsh_headless` pair once raw and managed tests cover two prompts in separate workers under one exact native ID. Qualify the installed `0.2.2-rc.3` build against self-hosted `Qwen/Qwen3.8-27B-FP8` using the existing DSH OpenAI Chat fixture inputs and each run's recorded private tmux socket. Check the cloud configuration under controlled preparation without sending provider requests. Migrate passive headless callers and fixture expectations. At spec synchronization update the old `dsh-headless-control` purpose sentence to describe native CLI control. Existing ACP records stay historical. Coordinate the release with 01, 02, and 04.
