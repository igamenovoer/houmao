# H1 Live Restart, Hello Turn, and Registry Permission Denial

Date: 2026-11-19. Status: the restarted H1 agent completed a gateway `hello` turn, but its attempts to inspect itself with `houmao-mgr agents self` initially failed against the DSH workspace sandbox. A temporary local patch adding the shared-registry root to DSH `additionalWritableRoots` made the exact command succeed in a fresh sandboxed run. The patch was then reverted at operator direction; [issue #86](https://github.com/igamenovoer/houmao/issues/86) proposes the product fix.

Plan: [Iteration 2](../iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md). Completed H1 results: [H1 native headless results](2026-11-19-h1-rc3-headless-execution.md).

## Restart

The first H1 agent had already been stopped, and the maintained fixture rejects launch from a stopped run. A fresh run was prepared with the same self-hosted Qwen, DSH `0.2.2-rc.3`, manager-headless, and isolated-tmux configuration:

- Run: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-3fc05c36f5b3`
- Agent: `085e0a1a-8b6e-43b2-b940-a15e134b6aa7`
- Runtime session: `dsh_headless-20261119-113226Z-a6038983`
- Native session: `session-3c771770-22f2-43a3-a1ae-e43ed05e52e6`
- Gateway: `http://127.0.0.1:45417`
- Tmux session: `HOUMAO-self-hosted-dsh-headless-manager-3fc05c36f5b3-1795087946554`
- Tmux socket: `/tmp/tmux-1001/houmao-fixture-self-hosted-dsh-headless-manager-3fc05c36f5b3`
- Attach script: `tmp/houmao-30-iter2-rc3/attach-live.sh`

The fresh run launched without an initial turn. `fixture.py check --live` reported no missing prerequisites, and a blank gateway usage collection showed the expected `headless_execution_binding_pending` state before the first turn. The tmux session contains only the supervisor shell; DSH headless has no interactive TUI.

## Hello Turn

The `hello` prompt was submitted through the fixture's authenticated gateway path. Turn `turn-ca85d9093faf` completed successfully and the pane ended with `[complete] native_completed`. The final response said the agent was ready and asked what to work on.

Observed cost and behavior:

- Wall time: 22.759 seconds.
- Provider calls: 17.
- Input tokens: 190,597.
- Output tokens: 1,579.
- Total tokens: 192,176.
- Final usage collection: healthy.

The turn was much more expensive than the prompt suggested. Before answering, the model explored its memo, mailbox, execution context, and manager state. Five later `bash` tool calls were malformed because the model omitted the required `command` property; each produced `Error: invalid arguments: missing required property "command"` and another provider round trip. The model eventually replied normally. This is recorded as model/tool-call behavior, not a failed managed turn.

## Permission Denial

During the same turn, the agent ran these commands from its `workdir`:

```bash
houmao-mgr agents self state
houmao-mgr agents self mail status
```

Both failed with the same path:

```text
Error: [Errno 13] Permission denied:
/data/huangzhe/code/houmao/tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-3fc05c36f5b3/registry/.managed-agent-locks/085e0a1a-8b6e-43b2-b940-a15e134b6aa7.lock
```

The exact command and result are in `manifest.turn-artifacts/turn-ca85d9093faf/stdout.jsonl` at the `agents self state` and `agents self mail status` tool calls. The model summarized the result as the registry being outside its workspace sandbox and continued without claiming success.

## Investigation and Root Cause

The following checks were made:

1. Captured the tmux pane and searched the turn artifact, canonical events, and native session journal for `denied`, `permission`, and `sandbox`.
2. Read the native DSH profile patch. It sets `sandbox-policy.mode` to `workspace-write`, approval policy to `never`, and selects the `houmao-unattended` preset.
3. Inspected the runtime system-reminder delivered to DSH. It states that writable modifications are limited to the session workspace at the run's `workdir` and that approval prompts are disabled.
4. Used `namei` and `stat` on the lock path. Every directory is owned by `huangzhe`, the lock file is mode `0600`, and the registry and lock directories are mode `0775`.
5. Opened the existing lock file read/write from an external owner process. The open succeeded, proving that Unix ownership and permission bits are not the cause.
6. Traced `houmao-mgr agents self state` and `agents self mail status` through current-session target resolution. The resolver resumes the runtime controller; `ensure_gateway_capability()` refreshes the shared registry record; registry publication calls `publish_managed_agent_record()`, which acquires `_managed_agent_record_lock()` and opens `.managed-agent-locks/<agent-id>.lock` with create/read-write flags.
7. Confirmed the same lock path is shared with executor-locator publication through `_identity_lock()` in the execution owner code.

The failure is therefore a sandbox boundary:

- DSH runs tool commands under `workspace-write`.
- The writable workspace is `.../runs/self-hosted-dsh-headless-manager-3fc05c36f5b3/workdir`.
- The shared registry is `.../runs/self-hosted-dsh-headless-manager-3fc05c36f5b3/registry`, a sibling outside that workspace.
- Even a command that looks read-only acquires the registry ownership lock, so DSH denies the file open with `EACCES`.

The gateway was healthy throughout, and the managed turn itself succeeded. The denial affects the agent's ability to call manager self-control commands from inside its own sandbox.

## Experimental Fix and Live Verification

The operator selected the `additionalWritableRoots` approach. A temporary local patch to `src/houmao/agents/dsh_configuration.py` resolved the selected environment's `HOUMAO_GLOBAL_REGISTRY_DIR` (falling back to normal Houmao registry precedence) and emitted:

```json
{
  "id": "sandbox-policy",
  "config": {
    "mode": "workspace-write",
    "additionalWritableRoots": [
      "<run-root>/registry"
    ]
  }
}
```

The setting remained absent for `as_is`, which continued to preserve native DSH permission defaults. The resolved registry path was passed explicitly to `prepare_dsh_home()` in the focused unit test. This grants the whole run-local registry, not only the lock directory, so all sandboxed commands in the session can write registry state. That is acceptable for the isolated fixture run but is a deliberate widening of trust.

The temporary code change was verified before the live rerun:

- `pytest -q tests/unit/agents/test_dsh_configuration.py tests/unit/agents/test_dsh_launch_surfaces.py`: 114 passed.
- `pixi run test`: 4,946 passed, 14 skipped.
- `pixi run lint`: passed.
- `pixi run typecheck`: no issues in 520 source files.

The product source and test changes were then reverted at operator direction. No implementation remains in the checkout; [issue #86](https://github.com/igamenovoer/houmao/issues/86) owns the proposal and least-privilege discussion.

The replacement live run is:

- Run: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-a82739454806`
- Agent: `6ee9ab0e-401c-4e40-8a91-3503aae8fe8b`
- Runtime session: `dsh_headless-20261119-114552Z-815a48f3`
- Native session: `session-141599c1-dac4-43e5-bc1b-e2a72316dce9`
- Gateway: `http://127.0.0.1:32815`
- Tmux session: `HOUMAO-self-hosted-dsh-headless-manager-a82739454806-1795088752125`
- The experimental agent was stopped after the verification, and its temporary attach wrapper was removed.

The generated home and runtime profile both contain the new run's registry in `additionalWritableRoots`. A gateway prompt asked the agent to run exactly `houmao-mgr agents self state`. Turn `turn-597c1b916a75` completed in 4.633 seconds with 16,082 total tokens, and the tool result was the full JSON state payload with `availability: available`. No permission-denied result appeared. The managed turn succeeded through the same DSH `workspace-write` sandbox that previously rejected the lock open.

## Remaining Caveat

The proposed fix would resolve the control-plane write boundary, but the broader alternatives remain relevant for less-privileged deployments:

- Make read-only manager operations such as `state`, `identity`, and mailbox `status` avoid registry publication and lock creation.
- Prefer external manager or authenticated gateway operations when self-control is not intentionally supported.

The original behavior remains a UX problem because DSH surfaced a policy denial as an OS-style `Permission denied` diagnostic rather than naming `additionalWritableRoots` as the missing grant.
