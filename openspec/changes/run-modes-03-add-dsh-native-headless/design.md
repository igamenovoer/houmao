# Design

## Context

DSH's native headless profile reads a task, projects JSON events, waits for the root and descendant work to settle, flushes the session, and exits. RC2's headless adapter runs `session/new` or `session/resume`, `session/prompt`, and `session/close` over a fresh ACP connection. Those are different execution contracts. [Native one-shot implementation](../../../extern/orphan/deepseek-harness/packages/bundle/headless/src/index.ts) and [RC2 ACP driver](../../../src/houmao/agents/realm_controller/backends/dsh_acp_driver.py).

## Goals / Non-Goals

Reuse Houmao's managed headless turn envelope, existing identity and usage journals, native role and home composition, and authenticated access. Bind the lifetime of one native headless process to one accepted prompt. Persistent ACP belongs to 04.

## Decisions

### Start a Native CLI Worker for Each Prompt

Register `dsh_headless` in the resolver, runtime, launch policy, tool-parameter checks, passive headless launch API, and fixture helper. Run the qualified executable with `--profile headless --json` and pass the task through private stdin. Omit `--session-id` for an explicit new conversation. For continuation, pass only the saved exact ID and original workspace. Honor DSH's preset, subagent, occupied-session and cwd validation. A saved ACP conversation may be incompatible. Never implicitly adopt it.

### Fence Between Process Startup and Native Input

Reuse the managed attempt and generation check. For immediate delivery, bind evidence and revocation to the actual native handoff, including the gap after stdin transfer and before DSH calls `followup`. Qualify the existing managed companion or an equivalent native hook on this profile. Without the necessary fence, refuse that immediate operation until qualified. A PID, accepted stdin, or JSON `session` line only proves the corresponding stage. [Managed companion](../../../src/houmao/agents/assets/dsh/managed-companion.mjs).

### Reconcile Events, Exit, and Journal

Capture raw NDJSON and stderr in private artifacts, bound surfaced diagnostics, and map events into the existing normalized stream. Match `sessionId` to the attempt. Combine native `final.reason`, exit status and flush evidence before setting a terminal outcome. Preserve native errors and partial output when the stream ends early. Interrupt only the verified owned process group and record the source of termination. Use the existing journal binding, source offsets and native attempt identities for usage, including retries and copied history. [JSON projection](../../../extern/orphan/deepseek-harness/packages/bundle/headless/src/json-stream.ts) and [DSH usage adapter](../../../src/houmao/agents/realm_controller/usage_adapters/dsh.py).

### Validate CLI Inputs on Their Own Terms

Keep the selected executable, private `DSH_HOME`, current materialized role, model, endpoint, credentials, native permission preset, and request overrides. Classify each MCP and skill input by its native read boundary. ACP `mcpServers` previously carried declarations during session binding. Prove an equivalent CLI-supported projection or explicitly reject the declaration in preflight. Ordinary prompts and observation leave materialized files intact. [DSH native configuration](../../../src/houmao/agents/dsh_configuration.py).

## Risks / Trade-offs

- A native error, cancelled process, or journal reset could look like success. Test malformed JSON, error without `final`, non-completion reasons, abnormal exit after output, interrupted descendants, and damaged journal continuity.
- A CLI launch can start while a stale client still holds dispatch permission. Exercise revocation immediately before native input and verify both the journal and managed receipt.

## Migration Plan

Enable the distinct `dsh_headless` pair once raw and managed tests cover two prompts in two workers under one exact native ID. Migrate passive headless callers and fixture expectations. At spec synchronization update the old `dsh-headless-control` purpose sentence to describe native CLI control. Existing ACP records stay historical. Coordinate the release with 01, 02, and 04.
