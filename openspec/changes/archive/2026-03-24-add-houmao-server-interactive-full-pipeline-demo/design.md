## Context

The repository already contains adjacent examples, but neither matches the exact pair-managed boundary needed for this change:

- the CAO interactive full-pipeline demo shows the desired operator workflow shape, but it is built around CAO-backed runtime-local launch behavior;
- the Houmao-server dual shadow-watch demo shows the supported `houmao-server + houmao-srv-ctrl` pair, but it is a monitoring workflow rather than an interactive full-pipeline walkthrough.

The current pair contract is now different from the earlier `houmao-cli`-centric startup model:

- `houmao-server` is the public HTTP authority for both `/houmao/*` and `/cao/*`;
- `houmao-srv-ctrl` is the supported pair CLI for compatibility-profile install and delegated terminal launch;
- `houmao-cli` remains available for uncovered or intentionally runtime-local workflows, but it is not the startup surface for this pair-native interactive demo;
- delegated `houmao-srv-ctrl launch` already materializes the runtime manifest and session root for `houmao_server_rest` and already calls `register_launch()` on the server side.

Current server behavior still adds one important constraint:

- `POST /houmao/agents/{agent_ref}/stop` is still headless-only in the current implementation, so a TUI demo cannot rely on that route yet for clean stop.

## Goals / Non-Goals

**Goals:**

- Provide a repo-owned interactive demo pack that is the Houmao-managed counterpart to the existing CAO full-pipeline demo.
- Launch through the supported `houmao-server + houmao-srv-ctrl` pair.
- Keep post-launch control in the demo on direct `houmao-server` HTTP calls.
- Persist enough run metadata to let follow-up commands address the same live managed agent and tracked terminal.
- Verify the workflow from server-owned request acceptance and tracked state rather than transcript wording.

**Non-Goals:**

- Replace or remove the existing CAO interactive demo.
- Use `houmao-cli` as the startup surface for this pair-native demo.
- Redesign the general `houmao-server` managed-agent API in this change.
- Add raw key-stream control to `houmao-server` for TUI sessions.
- Depend on exact assistant reply text as the verification contract.

## Decisions

### Decision 1: The new pack keeps the CAO demo's interactive operator shape, but startup is pair-native

The new pack will keep the familiar flow:

- `start`
- `inspect`
- `send-turn`
- `interrupt`
- `verify`
- `stop`

The boundary change is that startup uses the supported pair CLI:

- `houmao-srv-ctrl install ...`
- `houmao-srv-ctrl launch ...`

After that point, the demo will not call runtime control subcommands such as `houmao-srv-ctrl agents prompt`, `houmao-srv-ctrl agents gateway prompt`, `houmao-cli send-prompt`, `houmao-cli send-keys`, or `houmao-cli stop-session`.

Rationale:

- This matches the current pair contract in the repository rather than preserving an outdated `houmao-cli` startup assumption.
- It keeps the new pack recognizably equivalent to the existing interactive walkthrough instead of inventing a different operator model after launch.

Alternatives considered:

- Keep `houmao-cli` for build and launch: rejected because pair-native interactive startup now belongs to `houmao-srv-ctrl`.
- Rebuild the whole walkthrough around `houmao-srv-ctrl agents ...` follow-up commands: rejected because the demo is supposed to show direct `houmao-server` HTTP interaction after startup.

### Decision 2: Startup uses a demo-owned `houmao-server` listener and demo-owned run root

Each run will provision:

- a fresh run root under `tmp/demo/houmao-server-interactive-full-pipeline-demo/<ts>/`,
- a demo-owned `houmao-server` runtime root under that run root,
- a copied or worktree-based demo workdir under the run root,
- one loopback `api_base_url` selected and persisted for that run.

The demo will not assume an unrelated operator-managed `houmao-server` is already running.

The lifecycle implementation will live in a dedicated demo helper module and follow the existing dual-shadow-watch pattern: launch `houmao-server` as a subprocess via `sys.executable -m houmao.server serve`, capture stdout and stderr under the run root, and poll the server health route before startup proceeds.

Rationale:

- A demo-owned server makes the walkthrough reproducible and avoids mutating or depending on unrelated local state.
- Persisting the chosen base URL keeps follow-up commands simple even if the port is not fixed.
- Reusing the existing subprocess pattern from the dual-shadow-watch demo avoids inventing a second lifecycle mechanism.

Alternatives considered:

- Pin the demo to a fixed `http://127.0.0.1:9889`: rejected because it increases collision risk with unrelated local services.
- Require the operator to start the server manually: rejected because it weakens the demo's full-pipeline value.

### Decision 3: Startup installs one tracked compatibility profile and launches one delegated pair-managed TUI session

The demo will bundle one tracked compatibility-profile source and install it into the demo-owned server on each run through `houmao-srv-ctrl install`.

The launched interactive variant is then chosen by provider plus profile:

- default provider: `claude_code`
- explicit provider override: `codex`
- tracked profile name: `gpu-kernel-coder`

The demo will persist:

- `provider`
- resolved `tool`
- `agent_profile`
- `variant_id`
- `session_name`
- `terminal_id`
- canonicalized `agent_identity`

The `launch_alice.sh` convenience wrapper will keep the old operator intent by forwarding a fixed `--session-name alice` override rather than an `--agent-name` override.

Rationale:

- This keeps the demo aligned with the current pair-native launch contract, which is provider plus compatibility profile, not direct brain-recipe launch.
- The `gpu-kernel-coder` profile already matches the repository-scale engineering posture used by the older CAO demo.

Alternatives considered:

- Keep a recipe-first startup contract and translate it indirectly into pair launch: rejected because it would preserve an operator model that no longer matches the supported pair surface.
- Expose arbitrary install and launch profile inputs in v1: rejected because the demo should stay opinionated and equivalent, not become a generic pair wrapper.

### Decision 4: Pair-managed startup relies on delegated launch artifacts and auto-registration rather than a demo-owned registration step

For interactive delegated launches, `houmao-srv-ctrl launch` already:

- creates the terminal-backed session through the `houmao-server` pair,
- materializes the runtime-owned manifest and session root for `houmao_server_rest`,
- calls `register_launch()` so the session becomes addressable through managed-agent routes.

The demo will therefore not send its own extra `POST /houmao/launches/register` after startup.

Instead, startup will:

- set `AGENTSYS_GLOBAL_RUNTIME_DIR` explicitly for the delegated launch environment,
- discover the persisted runtime manifest from the pair-managed launch artifacts,
- treat the manifest `houmao_server` section as the startup-to-follow-up bridge,
- persist `session_name` as the stable v1 `agent_ref` for managed-agent routes.

Rationale:

- The pair-native launch path already owns delegated manifest creation and server registration.
- Sending a second registration request from the demo would duplicate pair logic and drift from the supported startup contract.
- `session_name` is already the tmux session identity, the delegated session identifier, and a valid managed-agent alias through current server resolution logic.

Alternatives considered:

- Keep a manual demo-side registration POST after launch: rejected because the pair launch already performs that step.
- Query `GET /houmao/agents` to discover a different primary identifier before first use: rejected because `session_name` is already sufficient and avoids a startup race.

### Decision 5: Post-launch interaction uses a split direct-server route strategy

The demo will use:

- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/state/detail`
- `GET /houmao/agents/{agent_ref}/history`
- `POST /houmao/agents/{agent_ref}/requests` with `request_kind=submit_prompt`
- `POST /houmao/agents/{agent_ref}/requests` with `request_kind=interrupt`
- `GET /houmao/terminals/{terminal_id}/state` for optional parser-derived text or detailed tracked-terminal inspection
- `DELETE /cao/sessions/{session_name}` for TUI teardown

This is intentionally mixed between Houmao-owned and CAO-compatible namespaces, but all calls still target the same `houmao-server` authority.

In v1, `agent_ref` means the persisted `session_name`, and `inspect` keeps parser-derived dialog tail output behind an explicit operator flag rather than showing it by default.

Rationale:

- Managed-agent routes already provide the correct server-owned surface for prompt, interrupt, and summary/detail inspection.
- TUI stop is not yet transport-neutral on `/houmao/agents/{agent_ref}/stop`, so `/cao/sessions/{session_name}` is the clean supported teardown path today.
- Matching the CAO demo's opt-in text-tail behavior keeps default inspect output focused on state while still allowing deeper terminal-derived text inspection when the operator asks for it.

Alternatives considered:

- Use `houmao-srv-ctrl agents prompt` or other pair CLI follow-up commands after launch: rejected because the demo is supposed to show direct server HTTP after startup.
- Use `POST /houmao/agents/{agent_ref}/stop` for TUI teardown: rejected because current implementation is headless-only.

### Decision 6: V1 excludes raw control-input parity and keeps verification server-state-based

The new demo will not ship a `send-keys` equivalent in v1.

The demo's verification contract will be built from:

- startup metadata (`provider`, `tool`, `agent_profile`, `variant_id`, `api_base_url`),
- accepted managed-agent request responses,
- persisted inspection snapshots from managed-agent or terminal-state routes,
- bounded turn outcome evidence derived from server-tracked state.

Verification will not require a verbatim assistant reply.

Rationale:

- The current direct server API does not expose a TUI raw control-input route equivalent to runtime `send-keys`.
- State-based verification stays stable across wording variation while still testing the intended operator flow.

Alternatives considered:

- Keep calling `houmao-cli send-keys` or pair CLI control commands after launch: rejected because it violates the requested server-only interaction boundary.
- Verify exact response text: rejected because it is brittle.

## Risks / Trade-offs

- [Delegated launch state is now owned by `houmao-srv-ctrl launch`] -> Set `AGENTSYS_GLOBAL_RUNTIME_DIR` explicitly for the demo-owned environment and keep manifest discovery tied to the delegated runtime root plus tmux manifest pointer.
- [Profile install and provider selection can drift from the older recipe-first CAO demo] -> Make the new provider-plus-profile contract explicit in the README and persist `provider`, `tool`, and `agent_profile` in demo state.
- [TUI stop still lives on `/cao/*` rather than a transport-neutral managed-agent stop route] -> Keep the stop implementation isolated so it can switch later.
- [Dropping `send-keys` from v1 makes the demo less feature-complete than the old CAO pack] -> Keep the scope explicit and leave raw control-input parity for a later server-API change.
- [Future server changes could prefer a server-assigned managed-agent identifier over `session_name`] -> Treat persisted `session_name` as the explicit v1 `agent_ref` contract and keep any later `tracked_agent_id` enrichment additive rather than required.

## Migration Plan

1. Add the new demo package, shell wrappers, and tracked compatibility-profile asset alongside the existing CAO interactive demo rather than replacing it.
2. Start a demo-owned `houmao-server` through a dedicated helper that follows the existing `sys.executable -m houmao.server serve` subprocess pattern.
3. Install the tracked compatibility profile into the demo-owned server through `houmao-srv-ctrl install`.
4. Launch one delegated TUI session through `houmao-srv-ctrl launch`, then discover the resulting runtime manifest and persisted `houmao_server` bridge state.
5. Persist `session_name` as the stable v1 `agent_ref` and implement follow-up commands over direct server HTTP routes.
6. Add unit and integration coverage for pair-managed startup, direct-server follow-up interaction, and stale-session teardown.
7. Update README and references so operators can choose the CAO demo or the Houmao-server pair demo depending on which boundary they need to validate.

## Deferred Follow-up

- When TUI stop becomes transport-neutral on `/houmao/agents/{agent_ref}/stop`, the demo can switch its teardown route without changing the rest of the v1 operator model.
