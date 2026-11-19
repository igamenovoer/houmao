# Iteration Plan 2: DSH Run Modes and Unified Control on RC3

Status: G0 passed; H1 completed on self-hosted Qwen with disposition **Needs revision** because detailed manager event replay rejects whitespace-only provider text chunks. The H1 agent was stopped cleanly. R0 and the other arms remain pending. Date: 2026-11-19. Campaign: [debug-intent.md](../debug-intent.md). Question owner: [KQ-1](../key-questions/KQ-1-dsh-basic-functionality.md). Evidence: [G0 and H1 preparation](../evidences/2026-11-19-rc3-iteration2-g0-and-h1-preparation.md) and [H1 results](../logs/2026-11-19-h1-rc3-headless-execution.md). Supersedes the unexecuted RC1/RC2 work in [Iteration 1](2026-11-18-plan-1-dsh-basic-functionality.md).

## Question and Revision Reason

Does Houmao `3.0.0rc3` operate DeepSeek Harness correctly under live human observation in each qualified run mode, with exact native continuation, truthful admission and outcomes, persistent usage, and clean ownership across manager, gateway, browser, and passive-server clients?

Iteration 1 targeted RC1 and used `dsh_acp` as the general headless path. RC3 makes that workflow `service`, adds native one-shot `headless`, replaces `--headless` and `--no-headless` with `--mode`, changes runtime schemas, and routes manager and gateway operations through one execution owner. The old plan and `iter1_dsh.py` therefore cannot provide RC3 coverage.

## Frozen Workload

- **Houmao baseline**: `3.0.0rc3`, tag `v3.0.0rc3`, release commit `4f3ba508`, invoked through `pixi run`. H1 executed at the subsequent commit `007ae801`, which contains only the separately approved checkout-`tmp` storage-policy fix and its tests/documentation. Record any later implementation change as a new baseline rather than mixing results.
- **DSH baseline**: explicitly selected `tmp/dsh/npm-runtime/node_modules/.bin/dsh`, version `0.2.2-rc.3`. Do not use ambient `dsh` resolution for qualification.
- **Qualified DSH modes**: `headless` → `dsh_headless`, `service` → `dsh_acp`, and `web` → `dsh_web`. DSH `tui` is unsupported and is a negative preflight case. Omitting the mode on a project launch defaults to `web`.
- **Runtime schemas**: launch plan 3, session manifest 6, managed-agent registry 5, and execution locator 2. RC2 agents must be stopped with RC2 before RC3 lifecycle operations. Retained RC2 records are diagnostic fixtures only, not service owners or relaunch candidates.
- **Scratch and access roots**: store all generated test inputs and runtime materials physically under the Git-ignored `tmp/houmao-30-iter2-rc3/` directory. Use `tmp/houmao-30-iter2-rc3/runs/` as `--run-root` and `tmp/houmao-30-iter2-rc3/inputs/iter2_dsh_system_prompt.txt` as the shared role. The fixture and gateway private-storage policies permit purpose-specific checkout `tmp/` run subdirectories while rejecting other checkout locations and unsafe permissions. Reusable auth stores remain external, and gateway access retains no-follow traversal. Preserve `tmp/houmao-30-iter1/` and `tmp/houmao-30-iter1-rc2/` as historical evidence. Use unique per-run tmux sockets, clear `TMUX`, `TMUX_PANE`, and `TMUX_TMPDIR`, and generate an exact attach script from each launch result.
- **Campaign tooling**: use `scripts/agents/test-fixtures/fixture.py` for maintained `prepare`, `launch`, `prompt`, `check`, `browser-connection`, and `stop` steps. Use `houmao-mgr agents single` and signed `GatewayClient` calls for owner and gateway-specific steps. `iter1_dsh.py` is RC1/RC2-only until rewritten; do not run its launch or profile commands against RC3.
- **Model lanes**: self-hosted `Qwen/Qwen3.8-27B-FP8` at the confirmed explicit OpenAI-compatible endpoint is the primary lane. DeepSeek is the secondary billable lane and requires an explicitly selected model and external env file. Never fall back between lanes or print credential values.
- **Shared prompts**: retain Iteration 1 role text and P1 through P4 unchanged so RC2 and RC3 observations remain comparable. P2 creates `dsh_probe.txt`; P3 appends to that file in the exact same native conversation; P4 runs `sleep 20 && echo FINISHED` for interruption and concurrent-client checks.

## Predeclared Arms

| Arm | Release surface and lane | Required live evidence |
| --- | --- | --- |
| R0 | RC3 setup, mode selection, and schema guardrails; no LLM call | Stored/direct `--mode`, default DSH `web`, DSH `tui` refusal, old-flag/helper containment, fresh schemas, and non-mutating RC2 diagnostic |
| H1 | DSH `headless`, self-hosted Qwen, manager plus signed gateway | P1–P4, one new worker per prompt with exact native session continuation, interrupt, native/canonical events, usage, refresh boundary, and stop |
| S1 | DSH `service`, self-hosted Qwen, manager plus signed gateway | P1–P4, persistent PID/session/incarnation, competing admission, detach/reattach during active work, exact relaunch, refresh boundary, and usage |
| W1 | DSH `web`, self-hosted Qwen, Chromium plus manager/gateway | Shared browser/API conversation, busy refusal, interruption, safe handoff, reattachment, history, and usage |
| V1 | Passive-server `dsh_headless`, self-hosted Qwen | Restart passive server after native handoff, preserve original turn and worker, expose canonical events/raw stdout, recover usage, and avoid replay |
| C1 | Maintained `fixture.py` cross-check, first available lane | `prepare`/`launch`/`prompt`/`check --live`/`stop` ergonomics; signed usage succeeds while unsigned private access fails |
| H2 | DSH `headless`, DeepSeek API | Repeat H1 after explicit billable-run approval |
| S2 | DSH `service`, DeepSeek API | Repeat S1 after explicit billable-run approval |
| W2 | DSH `web`, DeepSeek API | Repeat W1 after explicit billable-run approval |

The RC2 B1 log is preliminary evidence for S1 only. It does not mark S1 complete and provides no coverage for H1, W1, V1, or any DeepSeek arm.

## Command Contract

Use the maintained fixture with explicit inputs. The following prepares the Qwen native headless arm; use a new run directory for every arm and retain the returned `run_dir` privately:

```bash
export FIXTURE=scripts/agents/test-fixtures/fixture.py
export DSH_EXECUTABLE=/data/huangzhe/code/houmao/tmp/dsh/npm-runtime/node_modules/.bin/dsh

pixi run python "$FIXTURE" prepare \
  --case self-hosted --client dsh --mode headless --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"off":"none","low":"low","medium":"medium","high":"high"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --system-prompt-file tmp/houmao-30-iter2-rc3/inputs/iter2_dsh_system_prompt.txt \
  --run-root tmp/houmao-30-iter2-rc3/runs \
  --executable "$DSH_EXECUTABLE"
```

Change only the declared arm parameters: `service` for S1, `web` for W1, and `passive-server` for the V1 surface. DeepSeek arms use `--case cloud-api`, the selected external env file, and an explicit DeepSeek model instead of the Qwen route. Run launch and each later prompt as separate human-reviewed commands:

```bash
pixi run python "$FIXTURE" launch --run-dir "$RUN_DIR" --prompt '<P1 text>'
pixi run python "$FIXTURE" prompt --run-dir "$RUN_DIR" --prompt '<P2 text>'
pixi run python "$FIXTURE" prompt --run-dir "$RUN_DIR" --prompt '<P3 text>'
pixi run python "$FIXTURE" check --run-dir "$RUN_DIR" --live
pixi run python "$FIXTURE" stop --run-dir "$RUN_DIR"
```

For manager-owned agents, select the run-specific roots before direct manager follow-up. Without these exports, commands can incorrectly target the default pair authority at `127.0.0.1:9891`:

```bash
export HOUMAO_GLOBAL_REGISTRY_DIR="$RUN_DIR/registry"
export HOUMAO_GLOBAL_RUNTIME_DIR="$RUN_DIR/workdir/.houmao/runtime"
export HOUMAO_PROJECT_OVERLAY_DIR="$RUN_DIR/workdir/.houmao"
```

The canonical control shape is:

```bash
pixi run houmao-mgr agents single --agent-id "$AGENT_ID" state
pixi run houmao-mgr agents single --agent-id "$AGENT_ID" prompt --prompt '<prompt>'
pixi run houmao-mgr agents single --agent-id "$AGENT_ID" gateway detach
pixi run houmao-mgr agents single --agent-id "$AGENT_ID" gateway attach --background
pixi run houmao-mgr agents single --agent-id "$AGENT_ID" stop
pixi run houmao-mgr agents single --agent-id "$AGENT_ID" relaunch \
  --chat-session-mode exact --chat-session-id "$NATIVE_SESSION_ID"
pixi run houmao-mgr agents single --agent-id "$AGENT_ID" gateway detach
pixi run houmao-mgr agents single --agent-id "$AGENT_ID" gateway attach --background
```

Execute these commands through `pixi run` in the campaign shell. For Web, request `fixture.py browser-connection` explicitly and give the private descriptor only to the selected local browser consumer. Do not log sign-in tokens or cookies.

## Human-Watch Mechanics and Evidence

At every launch record `tool`, `mode`, `backend`, `native_surface`, agent ID, generation, native session, tmux socket, and exact attach command. Headless and service modes have no terminal handoff; their supervisor panes are diagnostic surfaces, not places to inject keystrokes. Web mode publishes only the safe browser origin and native session ID.

At every prompt record the request/turn ID, queue admission, native handoff, terminal outcome, uncertainty if present, worker PID or service incarnation, wall time, and finalized usage. Distinguish a successful CLI return from provider-confirmed completion. For concurrent tests, prove which request reached native input and prove the losing request was not replayed.

For one nontrivial Qwen turn in H1 and S1, select reasoning level 1 and use the selected surface's supported detailed event or display mode. Capture timestamped pane output and canonical events while the turn is active. Only provider-returned reasoning is observable evidence; do not require hidden chain-of-thought. Record whether output streams during processing or appears only at settlement, and identify any surface that cannot select detailed rendering.

For native-home refresh, use a harmless skill fixture and no real credential material. Headless must distinguish next-invocation discovery from a live worker; service must distinguish provider-start and session-binding boundaries and require exact relaunch where documented; Web uses its own qualified native observation path. Never treat an edited file's presence as proof that a running provider loaded it.

## Gates

Gates are ordered. A failed gate blocks dependent arms but does not justify changing production code within this campaign.

- **G0 — Release and containment**: Confirm RC3 and DSH versions, explicit provider routes, fresh roots, isolated tmux, and default-server preservation. Stop any remaining RC2 agent through an RC2-owned control path before using RC3 against that identity. No RC3 command may take ownership of the retained RC2 B1 manifest.
- **G1 — Setup and mode selection**: Verify stored and direct `--mode`, DSH default `web`, unsupported `tui` refusal before home mutation, current schema versions, and explicit legacy-schema guidance. Confirm no campaign command emits `--headless` or `--no-headless`.
- **G2 — Native headless**: P1 preserves both literal markers; P2 writes `ONE-LINE-OK`; P3 appends `RESUMED-OK` in the same native session through a different worker; P4 interrupts the exact worker. Native JSON, canonical events, process closure, and usage agree. `send-keys` and ACP-only MCP declarations fail explicitly.
- **G3 — Persistent service**: Successive manager and signed-gateway prompts retain one service incarnation and native session. A competing request receives a truthful busy result. Gateway detach during P4 leaves the owner and request alive, manager control still works, and reattachment neither duplicates the worker nor replays input. Exact relaunch changes the incarnation and preserves the selected native conversation.
- **G4 — Web coexistence**: Browser and API output belong to one native conversation. `ready_only` refuses a programmatic prompt while the browser owns active work, without deferred mutation. Interrupt and gateway reattachment preserve history and public state remains token-free.
- **G5 — Passive and auth observability**: Passive restart after native handoff retains the original turn identity and at most one native admission. Canonical events, raw stdout, and usage remain available. Unsigned private routes return the expected authentication error; enrolled admin proof succeeds. A signed `401` is a failure, not an expected fixture outcome.
- **G6 — Teardown**: Stop each owned agent through its captured identity, close only campaign tmux servers, retain evidence, and verify no owned service, worker, gateway, or browser host remains. Do not kill the default tmux server.

## Decision Rules

- Classify each arm separately as **Works as designed**, **Works with caveats or UX friction**, **Needs revision**, or **Not run**. Automated RC3 change-local qualification is supporting evidence, not a substitute for these watched runs.
- If Qwen fails while DeepSeek succeeds, isolate provider protocol, DSH native behavior, and Houmao owner/control behavior before assigning a root cause.
- Treat a new worker PID in headless mode as expected and a new native session as a failure. Treat a persistent service PID/incarnation across ordinary prompts as expected and an unrequested replacement as a failure.
- Treat uncertain native handoff or terminal outcome as a result to preserve, never as permission to retry automatically. Count provider admissions when checking for replay.
- Record CLI, browser, event-stream, and authentication friction even when the underlying turn completes. The RC2 gateway signer failure remains a UX regression input until the equivalent RC3 maintained path is shown to select accepted proof correctly.

## Execution Checklist

- [x] Complete G0 for the H1 start, including RC2 containment and fresh RC3 roots; repeat provider checks for each later lane
- [ ] Complete R0 and record G1 results (DSH `tui` negative selection passed during preparation)
- [x] Complete H1 and evaluate G2 (core lifecycle passed; detailed event replay failed, so H1 needs revision; owned agent stopped)
- [ ] Run S1 and evaluate G3
- [ ] Run W1 and evaluate G4
- [ ] Run V1 and C1, then evaluate G5
- [ ] After explicit approval, run H2, S2, and W2 on DeepSeek
- [ ] Write dated evidence and discussion records for every executed arm and failure
- [ ] Evaluate G6 and update KQ-1 and the campaign status

## Result

G0 passed for the H1 Qwen start, and DSH `tui` was rejected correctly during an R0 negative check. The checkout-`tmp` storage-policy fix was separately requested, implemented, and verified with 4,946 passing unit tests, full Ruff lint, strict mypy, and a strict documentation build. H1 completed P1–P4 with one native session, a different worker per prompt, correct file effects, finalized completed/interrupted usage, and clean teardown. Reasoning level 1 selected native `low`; provider reasoning and progress appeared in raw artifacts during execution, and a newly added skill loaded on the next invocation. `send-keys` and ACP-only MCP declarations failed explicitly. H1 is **Needs revision** because `turn events --detail detail` rejects whitespace-only assistant events with a `HoumaoHeadlessTurnEvent.message` validation error, and the supervisor pane showed no live output. R0 and all other arms stay pending. See the [preparation and P1 evidence](../evidences/2026-11-19-rc3-iteration2-g0-and-h1-preparation.md), [complete H1 evidence](../logs/2026-11-19-h1-rc3-headless-execution.md), and [storage-policy fix log](../logs/2026-11-19-checkout-tmp-storage-policy-fix.md).

Separately, live H1 observation found that `houmao-mgr agents self state` and mailbox `status` were denied when they tried to acquire the shared-registry lock outside the DSH workspace sandbox. The operator approved a temporary experiment with DSH `additionalWritableRoots`. A local patch projected the run registry into the unattended sandbox profile; a fresh sandboxed run then executed `houmao-mgr agents self state` successfully. Focused tests, full unit tests (4,946 passed, 14 skipped), Ruff, and strict mypy passed. The operator directed that the product and test changes be reverted; no implementation remains. The proposed fix, privilege trade-offs, and verification evidence are recorded in [issue #86](https://github.com/igamenovoer/houmao/issues/86), with the campaign details in the [denial and experiment log](../logs/2026-11-19-h1-live-hello-and-registry-permission-denial.md).

## Required Follow-On Outside This Iteration

RC3 also adds Kimi ACP service, Kimi Web, and Codex app-server service, and it makes mode selection and handoff common across Claude, Codex, Kimi, and DSH. Plan a separate cross-tool iteration for the qualified matrix, including unsupported combinations, TUI versus Web handoff, persisted mode across profile edits and relaunch, owner-bound control, AG-UI observation, and usage. Existing change-local Qwen logs do not mark that campaign coverage complete.
