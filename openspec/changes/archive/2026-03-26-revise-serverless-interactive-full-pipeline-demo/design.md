## Context

The current demo pack is built around a demo-owned `houmao-server`: startup provisions a loopback server, launches one detached delegated TUI session through the native headless launch API, then persists `api_base_url`, `agent_ref = session_name`, and server-owned bridge metadata for every later action. That design matched an earlier pair-managed story, but it now conflicts with the newer Houmao split where `houmao-mgr agents launch` and the underlying runtime stack can build, launch, discover, and control local managed agents without `houmao-server`.

This change is scoped to the existing `scripts/demo/houmao-server-interactive-full-pipeline-demo/` pack. The pack path stays stable, but its runtime contract changes from server-backed to serverless/local. The repo already has the key primitives needed for this redesign:

- local launch through brain build + `start_runtime_session()`
- shared-registry publication for later discovery
- registry-first local target resolution in `srv_ctrl.commands.managed_agents`
- local prompt, interrupt, stop, gateway, and mailbox control through resumed `RuntimeSessionController`
- local TUI inspection through `SingleSessionTrackingRuntime`

The main challenge is not adding new runtime capability; it is revising the demo contract, persisted state, and inspection surfaces so they teach the current local architecture clearly and deterministically.

## Goals / Non-Goals

**Goals:**

- Keep the existing demo pack path and wrapper surface, but revise it to launch locally without starting `houmao-server`.
- Make the demo persist the modern identity model: `agent_name`, `agent_id`, `tmux_session_name`, and `manifest_path`.
- Align follow-up demo actions with local registry/controller behavior rather than pair HTTP routes.
- Preserve the demo's current operator workflow shape (`start`, `inspect`, `send-turn`, `interrupt`, `verify`, `stop`) and its demo-owned run root with machine-readable artifacts.
- Keep inspection and verification transcript-light by relying on local tracked state, detail, and history rather than exact assistant wording.

**Non-Goals:**

- No changes to `mail-ping-pong-gateway-demo-pack`.
- No changes to the public `houmao-mgr` feature contract unless an implementation gap is discovered while applying this change.
- No attempt to preserve the current persisted state schema or the current demo-owned `houmao-server` artifact layout.
- No new collaboration or mailbox workflow in this demo pack; it remains a single-agent interactive pipeline demo.

## Decisions

### 1. Keep the existing demo pack identity, but change its runtime model

The path `scripts/demo/houmao-server-interactive-full-pipeline-demo/` remains the canonical operator entrypoint so existing references do not need a second demo pack. However, the pack will stop modeling itself as a pair-managed validator and instead become a local interactive managed-agent demo that happens to keep its historical directory name.

Alternative considered:

- Rename the pack and create a new spec/capability. Rejected because the user explicitly wants this pack revised rather than replaced, and the repo already has an archived capability for this path.

### 2. Launch directly through local runtime APIs, not by shelling out to `houmao-mgr agents launch`

The demo should perform local build and launch by calling the same underlying Python surfaces that `houmao-mgr agents launch` uses: resolve the native selector, build the brain home, and call `start_runtime_session()` with a local interactive backend. This keeps the demo deterministic, avoids CLI trust prompts, avoids parsing human CLI output, and preserves the demo's existing pattern of writing rich machine-readable state immediately after startup.

Alternative considered:

- Shell out to `houmao-mgr agents launch --headless` or interactive mode and parse its output. Rejected because the demo needs precise startup artifacts and should not depend on CLI prompt suppression or text parsing.

### 3. Persist the managed-agent identity tuple explicitly and stop treating tmux session name as the control ref

The revised state model will replace the old `api_base_url`, `agent_ref`, `agent_identity`, and `houmao_server` bridge-centric contract with a local contract centered on:

- `agent_name`
- `agent_id`
- `tmux_session_name`
- `session_manifest_path`
- `session_root`
- demo-owned runtime / registry / jobs / workspace paths

`requested_session_name` may still be recorded for operator transparency, but it will remain a tmux handle request, not the managed-agent reference. Follow-up commands should resolve the live target through `agent_id` when available and otherwise by `agent_name`.

Alternative considered:

- Preserve `agent_ref = session_name` as a compatibility alias inside the demo. Rejected because the point of the revision is to teach the newer identity split rather than restate the older server-route model.

### 4. Reuse registry-first managed-agent helpers for follow-up control where possible

For prompt, interrupt, stop, and managed-agent state/detail/history views, the demo should reuse the same local/serverless control logic already exercised by `srv_ctrl.commands.managed_agents`. Concretely, the demo can resolve a local target from persisted identity data and then use the shared helper functions or resumed controller methods that those helpers already wrap.

This keeps the demo behavior aligned with the public `houmao-mgr agents ...` operator model without forcing the demo to shell out through the CLI.

Alternative considered:

- Re-implement separate demo-local control logic directly against tmux and runtime internals. Rejected because it would duplicate the already-supported local control path and risk teaching a private workflow.

### 5. Use local shared TUI tracking for inspect and verify

The current demo obtains inspect data from `houmao-server` managed-agent and tracked-terminal routes. The revised demo will instead resume the local controller and project local tracked TUI state through the existing `SingleSessionTrackingRuntime`-based helpers. This keeps inspect output focused on non-text operational evidence and preserves the existing opt-in dialog-tail behavior without reintroducing server ownership.

Alternative considered:

- Reduce inspect to static manifest-only data. Rejected because the demo is supposed to teach a live interactive pipeline and needs live state, turn posture, and stability evidence.

### 6. Keep a demo-owned run root, but remove demo-owned server artifacts

The pack will continue to own its run root, copied worktree, runtime root, registry root, jobs root, and generated reports. The run root layout will drop `server/`, server PID/log metadata, and any expectation that live artifacts are rooted under `runtime/sessions/houmao_server_rest/...`. Instead, startup and verification artifacts should point at the local runtime session manifest and local tracking evidence.

Alternative considered:

- Switch fully to ambient global runtime directories. Rejected because demo-local ownership is valuable for cleanup, reproducibility, and inspection.

## Risks / Trade-offs

- **Historical pack name still contains `houmao-server`** → Mitigation: explicitly document in README and spec that the pack keeps its path for continuity while teaching the current local/serverless model.
- **Local interactive startup can be less deterministic if provider readiness changes** → Mitigation: continue using explicit demo-owned startup budgets and direct runtime APIs so startup can validate ready posture before success is reported.
- **Friendly-name lookup could become ambiguous if multiple local agents share a name** → Mitigation: persist the effective `agent_id` and prefer exact-target resolution through `agent_id` in follow-up commands.
- **Inspect output may differ from prior server-owned shapes** → Mitigation: keep the demo's machine-readable inspect/report artifacts stable at the demo layer even if their live evidence now comes from local tracking rather than pair routes.
- **Some local gateway/notifier operations are richer at the gateway HTTP layer than in the current `houmao-mgr agents gateway` CLI** → Mitigation: this demo remains single-agent and does not need to expand into the mailbox/gateway collaboration story.

## Migration Plan

1. Update the demo spec delta so the required contract no longer references demo-owned `houmao-server` startup, `agent_ref = session_name`, or direct server routes.
2. Refactor the demo state and startup flow to build and launch a local managed agent and persist the new identity tuple.
3. Refactor inspect, prompt, interrupt, verify, and stop to resolve the local managed agent through the shared registry/controller path.
4. Rewrite README and shell-wrapper language to describe the serverless/local managed-agent flow and the new run-root artifacts.
5. Update unit and integration coverage to assert the local runtime contract.

Rollback strategy: revert the demo pack changes and the corresponding spec delta together if the local startup/control path proves insufficient for this tutorial workflow.

## Open Questions

- Should the demo choose a fixed `agent_name` like `alice` by default, or should it derive a variant-specific friendly name while keeping `launch_alice.sh` as the stable named example?
- Should `inspect` continue exposing an explicit dialog-tail excerpt in the same top-level field shape, or should it shift to a tracking-oriented substructure that mirrors local managed-agent detail more closely?
