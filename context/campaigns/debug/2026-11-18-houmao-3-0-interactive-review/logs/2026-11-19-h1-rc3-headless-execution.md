# RC3 Iteration 2 H1 Native Headless Results

Date: 2026-11-19. Status: H1 executed completely on self-hosted Qwen and stopped; disposition **Needs revision** because detailed manager event replay rejects provider output containing whitespace-only text chunks. Core prompting, exact continuation, interruption, next-invocation skill loading, negative capability checks, usage, and teardown passed.

Plan: [Iteration 2](../iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md). Preparation and P1: [G0 and H1 preparation](../evidences/2026-11-19-rc3-iteration2-g0-and-h1-preparation.md). Question: [KQ-1](../key-questions/KQ-1-dsh-basic-functionality.md).

## Identity and Baseline

- Houmao `3.0.0rc3`, executed at commit `007ae801` after the release baseline `4f3ba508`; the intervening commit contains the separately approved checkout-`tmp` storage-policy fix.
- DSH `0.2.2-rc.3`, explicitly selected from `tmp/dsh/npm-runtime/node_modules/.bin/dsh`.
- Model `Qwen/Qwen3.8-27B-FP8` through `http://127.0.0.1:14888/v1`.
- Run: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-4098c41338ef`.
- Agent: `fd4e2343-7ed5-4346-8105-a645933fde83`.
- Runtime session: `dsh_headless-20261119-103743Z-2b2c438d`.
- Native session, unchanged across all native turns: `session-5b3b8aa7-7390-4245-bcda-d8183c4cd968`.
- Gateway: `http://127.0.0.1:38605`; tmux socket: `/tmp/tmux-1001/houmao-fixture-self-hosted-dsh-headless-manager-4098c41338ef`.

The agent already existed and had completed P1 when this execution resumed. It was reused rather than duplicated. P2 through P4 used the maintained fixture's authenticated gateway path. The reasoning/skill and MCP checks used `houmao-mgr agents single` with the run-specific registry, runtime, and project-overlay roots.

## Prompt and Lifecycle Results

| Check | Turn | Worker child PID | Outcome and usage |
| --- | --- | ---: | --- |
| P1 literal preservation | `turn-2d66cb64e363` | 613773 | Completed; `{{ITER1_LITERAL}} $KEEP_LITERAL OK`; 6,786 total tokens |
| P2 create and `pwd` | `turn-e982faf8b295` | 814571 | Completed; `dsh_probe.txt` contained exactly `ONE-LINE-OK`, `pwd` returned the run workdir, final text `DONE`; 21,098 total tokens across three provider requests |
| P3 exact continuation and append | `turn-d5648505e9ed` | 817166 | Completed; file retained `ONE-LINE-OK` and gained `RESUMED-OK`, final text `RESUMED`; 22,248 total tokens across three provider requests |
| P4 interruption during `sleep 20` | `turn-d51be13566b1` | 819486 | Interrupted with return code 130 after 9.390 seconds; partial usage 7,653 tokens; gateway returned to healthy idle |
| Reasoning and next-invocation skill probe | `gwreq-20261119-112644Z-40f3a4c2` | 832029 | Completed; final text `H1-NEXT-INVOCATION-DISCOVERED 5461`; 25,550 total tokens across three provider requests |

P1 through P4 are present in the fixture's signed usage collection, which remained healthy with no diagnostics. The reasoning/skill turn has its own finalized `usage-record.json` and `usage-final.json` under `manifest.turn-artifacts/gwreq-20261119-112644Z-40f3a4c2/`; the fixture's cached `run.json` summary was not refreshed by the direct manager command and therefore lists only P1 through P4.

P4's blocked prompt caller failed with `Managed turn did not complete; inspect public usage`, as expected after interruption. Raw stdout ended with `flush on a closed handle` after the active bash call. Final usage explicitly records `outcome: interrupted`, partial token availability, and the native `turn/end` interruption observation.

## Reasoning, Streaming, and Native-Home Refresh

The manager command selected `--reasoning-level 1`. Native journal evidence contains `model/selection` and `request/header` records with `reasoningEffort: low`, and the invocation patch also selects `low`. Provider-returned `thinking` events were appended to `stdout.jsonl` and `canonical-events.jsonl` while the turn was active, before the bash tool completed and before final settlement. This answers the streaming question for durable artifacts: reasoning and progress are available during processing, not only in the final response.

The supervisor pane capture was empty during the active turn, so the pane did not provide a useful live display. `turn events --detail detail` is a persisted-event replay command, not a streaming subscription. Its active-turn invocation at `2026-11-19T11:26:57Z` failed with:

```text
HoumaoHeadlessTurnEvent.message: Value error, must not be empty
input_value='\n\n'
```

The canonical artifact contains whitespace-only assistant events immediately after provider reasoning. Raw native and canonical JSON remained readable, but the supported detailed manager rendering path did not work for this provider output.

A harmless skill was created at the runtime native home under `skills/h1-next-invocation-probe/SKILL.md`. `refresh --check` reported skills as supported at `component: next_invocation`, `boundary: next_turn`, with freshness unknown; MCP was unsupported with `dsh_cli_mcp_unqualified`. `refresh` returned `outcome: unsupported` and `effects: absent` without creating a turn. The following ordinary manager invocation loaded the skill through DSH's `skill` tool and returned its marker, proving next-invocation discovery rather than assuming discovery from file presence.

## Negative Capability Checks

Gateway `send-keys --sequence '<[Escape]>'` failed explicitly with `unsupported_capability`:

```text
Managed control operation 'send_keys' is unsupported for dsh headless (dsh_headless).
```

A temporary stdio MCP declaration named `h1-acp-only-probe` was added to the runtime home's `houmao-tool-params.yaml`, then restored after the check. Turn `gwreq-20261119-112727Z-a15f0aad` failed with return code 1 and:

```text
DSH headless cannot project ACP MCP declarations 'h1-acp-only-probe' (stdio) to the native CLI.
```

The unique prompt `ACP-MCP-SHOULD-NOT-REACH-NATIVE` does not occur in the native session journal. The artifact has no native session binding, native handoff, native evidence, or provider token usage. A wrapper runner and child process did start and exited with code 1; the verified boundary is no native handoff or native work, not absence of a wrapper process.

## Control-Path Correction

Initial unscoped `state`, `refresh --check`, and `gateway send-keys` commands attempted the default pair authority at `127.0.0.1:9891` and failed with connection refused. No run state changed. The fixture README requires these run-specific roots for direct manager follow-up:

```bash
export HOUMAO_GLOBAL_REGISTRY_DIR="$RUN_DIR/registry"
export HOUMAO_GLOBAL_RUNTIME_DIR="$RUN_DIR/workdir/.houmao/runtime"
export HOUMAO_PROJECT_OVERLAY_DIR="$RUN_DIR/workdir/.houmao"
```

After selecting those roots, `state` and `gateway status` worked, `send-keys` reached the intended unsupported-capability check, and the reasoning/skill turn completed. This is recorded as operator-command friction and the Iteration 2 command contract now includes the required exports.

## Teardown

`fixture.py stop --run-dir <run>` returned `status: stopped` and `cleanup: stopped_owned_identity`. The exact H1 tmux session was absent afterward, the gateway no longer accepted HTTP connections, and `os.kill(pid, 0)` confirmed that none of the captured gateway, P1–P5, or MCP-negative wrapper/child PIDs remained. No default tmux server or RC2 diagnostic agent was modified.

## Disposition and Follow-Up

H1 **Needs revision**. The native headless lifecycle itself passed on Qwen, including different workers with exact native-session continuation, but the detailed manager event-replay path cannot render the observed reasoning stream. Preserve the raw artifacts as reproduction evidence. Any production fix requires separate explicit approval; this campaign run changed no production source or committed tests.
