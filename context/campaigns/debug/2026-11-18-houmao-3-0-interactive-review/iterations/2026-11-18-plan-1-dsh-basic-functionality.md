# Iteration Plan 1: DSH Basic Functionality With Houmao

Status: superseded for RC3; partially executed on RC2. Date: 2026-11-18. Revised: 2026-11-19. Campaign: [debug-intent.md](../debug-intent.md).

Question owner: [KQ-1](../key-questions/KQ-1-dsh-basic-functionality.md). Evidence: [B1 RC2 Qwen 3.8 launch and gateway prompt](../logs/2026-11-19-b1-rc2-qwen38-launch-and-gateway-prompt.md). Current execution plan: [Iteration 2](2026-11-19-plan-2-dsh-rc3-run-modes.md).

This file preserves the original frozen RC1 plan for traceability. Do not run its commands unchanged against RC3. RC3 replaces `--headless` and `--no-headless` with `--mode`, maps the earlier DSH ACP workflow to `service`, and adds a distinct native one-shot `headless` mode. The Result section records which steps actually ran.

## Question / Answer Sought

Does DeepSeek Harness (`dsh` `>=0.2.2-rc.1`, release or `rc` only) work cleanly with Houmao `3.0.0rc1` across basic `dsh_acp` (headless) and `dsh_web` (interactive Web) workflows when a human watches execution step by step on both the DeepSeek API (`cloud-api`) and self-hosted Qwen 3.8 (`self-hosted`) model lanes? Deliverables are step-by-step live observation logs, human UX/correctness review notes per arm, and an evidence-backed disposition for `KQ-1.1` through `KQ-1.4`.

## Frozen Workload

- **Houmao codebase and CLI**: Branch `devel` (`3.0.0rc1`) with the 2026-11-18 DSH lower-bounded version floor revision (`>=0.2.2rc1`, release and `rc` only, no upper bound), invoked via `pixi run houmao-mgr`.
- **DSH runtime**: Default `PATH` `dsh` (`~/.bun/bin/dsh`, `0.2.2-rc.1` = npm `latest`) or isolated `tmp/dsh/npm-runtime/node_modules/.bin/dsh` (`0.2.2-rc.3`). Both satisfy `>=0.2.2-rc.1`; Arm A0 verifies that default `PATH` `dsh` resolves cleanly without `PATH` overrides while synthetic `0.2.2-alpha.3` or `0.2.1` shims are rejected.
- **Campaign runner and tmux isolation**: Iteration 1 helper implementations live in [scripts/explore/houmao-3-0-interactive-review/](../../../../../scripts/explore/houmao-3-0-interactive-review/) (`common.py` and `iter1_dsh.py`). All managed launches clear inherited `TMUX` and `TMUX_PANE` and target an isolated tmux server `-L houmao-30-iter1` (via a `0700` `tmux` shim generated under `tmp/houmao-30-iter1/bin/tmux`, matching the [fixture helper convention](../../../../../scripts/agents/test-fixtures/fixture.py)) plus `HOUMAO_GLOBAL_*` state directories under `tmp/houmao-30-iter1/houmao-state/`. Active user sessions (`mao-1..4`, `rsi-1..4`) remain untouched. The human watches live by attaching in a separate terminal with `env -u TMUX -u TMUX_PANE tmux -L houmao-30-iter1 attach`, or via explicit `capture-pane` snapshots at pause checkpoints.
- **Scratch and private access directories**: Project overlays, workdirs, launch profiles, and runtime artifacts live in the gitignored repository scratch directory `tmp/houmao-30-iter1/` rather than system `/tmp`. Because `houmao.gateway._access_storage` rejects any ancestor directory containing `.git`, generated Ed25519 admin keys, `gateway-admin-seed.json`, and `XDG_CONFIG_HOME` (`gateway-access/`) live under `~/.local/state/houmao-30-iter1/` (`0700`/`0600`).
- **Model lanes**:
  - **DeepSeek API (`cloud-api`)**: Uses credentials sourced from project `.env` (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL_ANTHROPIC`) copied into an external `0600` file for fixture compatibility, `adapter: deepseek`, `protocol: messages`, `route: deepseek-official`, and an operator-confirmed DeepSeek model (for example `deepseek-chat`) with explicit `context_window`, `max_output_tokens`, and `reasoning` metadata.
  - **Self-hosted Qwen 3.8 (`self-hosted`)**: Uses `adapter: pi-ai`, `protocol: openai-completions`, `route: houmao-self-hosted` (or `houmao-compatible`), explicit `Qwen/Qwen3.8-27B-FP8` (or confirmed served ID), active OpenAI-compatible base URL (historically `http://127.0.0.1:14888/v1`), context window `262144`, and confirmed `max_output_tokens` and `reasoning` settings.
- **Frozen prompts (shared across arms)**:
  - **Role prompt template**: `"Always preserve literal marker {{ITER1_LITERAL}} and $KEEP_LITERAL. Be concise."` (verifies additive `interpolate: false` injection).
  - **P1 (Literal prompt & basic turn)**: `"Reply with your exact literal marker from your instructions and OK. Do not use tools."`
  - **P2 (Tool-call file oracle)**: `"Create a file named dsh_probe.txt in the current working directory containing exactly ONE-LINE-OK, then run pwd and reply with DONE."`
  - **P3 (Exact continuation)**: `"Read dsh_probe.txt and append a second line RESUMED-OK without replacing the first line, then reply with RESUMED."`
  - **P4 (Interruptible shell turn)**: `"Use the shell tool to run sleep 20 && echo FINISHED, wait for it to finish, and then reply."` (operator invokes `interrupt` after confirming active execution, then inspects `state` and `usage`).

## Predeclared Arms

| Arm | Mode and Surface | Model Lane | What Is Executed and Watched Live |
| --- | --- | --- | --- |
| A0 | Setup & guardrail probe (`houmao-mgr` CLI, no LLM call) | None | Initialize `tmp/houmao-30-iter1/proj-a0`; verify default `PATH` `dsh` (`0.2.2-rc.1`) passes version checks, test starter `dsh-setup.yaml` with `models: []`, test synthetic `0.2.2-alpha.3` / `0.2.1` rejection, and check credential setup UX |
| A1 | `dsh_acp` headless via `houmao-mgr` + live gateway | `cloud-api` (DeepSeek API from `.env`) | Create `deepseek` credential, populated `dsh-setup.yaml`, specialist, and `--headless` profile; launch on `-L houmao-30-iter1`; watch tmux console + gateway logs through P1, P2, P3, P4+interrupt, `state`, `GET /v1/usage`, and `stop` |
| A2 | `dsh_web` interactive Web via `houmao-mgr` + live browser | `cloud-api` (DeepSeek API from `.env`) | Launch `--no-headless --gateway-background`; inspect published origin and private sign-in handoff; open native Web UI; test human browser prompt, API prompt (`P1`/`P2`), busy `ready_only` refusal while browser is generating, `interrupt`, `usage`, and `stop` |
| B1 | `dsh_acp` headless via `houmao-mgr` + live gateway | `self-hosted` (Qwen 3.8 via `pi-ai`) | Repeat the A1 `dsh_acp` sequence against the active Qwen 3.8 endpoint (`pi-ai/openai-completions`), watching tool calls, reasoning behavior, exact resume, interrupt, and `usage` |
| B2 | `dsh_web` interactive Web via `houmao-mgr` + live browser | `self-hosted` (Qwen 3.8 via `pi-ai`) | Repeat the A2 `dsh_web` browser plus API coexistence sequence on self-hosted Qwen 3.8 (contingent on B1 endpoint availability and compatibility) |
| C1 | Cross-check via `scripts/agents/test-fixtures/fixture.py` | Either available lane | Prepare and check one `fixture.py` manager run to evaluate fixture ergonomics and verify whether `fixture.py check --live` hits `3.0.0rc1` gateway auth (`401` on `/v1/usage`) or succeeds |

## Human-Watch Mechanics

Each live arm (`A1`, `A2`, `B1`, `B2`) runs interactively through stepwise `iter1_dsh.py` subcommands (`setup-arm`, `launch`, `send`, `interrupt`, `watch`, `stop`) with explicit operator pause points after Launch, P1, P2, P3, P4+Interrupt, Usage/State Inspection, and Stop. At each checkpoint, `iter1_dsh.py` displays:

1. The exact attach command (`env -u TMUX -u TMUX_PANE tmux -L houmao-30-iter1 attach -t <session>`) and a current `capture-pane` excerpt.
2. Gateway listener details (`port`, `agent_id`, recent log lines, and whether authenticated proof is required for `/v1/usage` or `/v1/state`).
3. For `dsh_web` (`A2`, `B2`), the clean origin URL and private sign-in instructions (kept out of tracked campaign logs) so the human can watch the Web UI directly or review the captured state/browser actions.

## Gates

Gates are evaluated in order before advancing to dependent arms:

- **G0 (Prerequisites & Isolation Gate)**: Confirm host `dsh --version` (`0.2.2-rc.1`) and isolated `tmp/dsh/npm-runtime/node_modules/.bin/dsh --version` (`0.2.2-rc.3`) satisfy `>=0.2.2-rc.1`, verify isolated tmux server `houmao-30-iter1` creates and lists a test window without touching `mao-1..4` or `rsi-1..4`, confirm DeepSeek `.env` variables are populated (without printing values), and probe the self-hosted Qwen 3.8 `/v1/models` endpoint (if unreachable, Arms A0/A1/A2 proceed on DeepSeek API while B1/B2 pause until the Qwen tunnel/server is active).
- **G1 (A0 Setup Clarity Gate)**: All pre-launch failure modes (unsupported `0.2.1` or `0.2.2-alpha.3` rejection, empty `models: []` error, missing credential error) produce explicit, understandable diagnostics while default `PATH` `dsh` (`0.2.2-rc.1`) passes version validation; human rates onboarding friction.
- **G2 (A1/B1 Headless Functional Gate)**: P1 preserves `{{ITER1_LITERAL}}` and `$KEEP_LITERAL`; P2 writes `ONE-LINE-OK` to `dsh_probe.txt`; P3 appends `RESUMED-OK` on the same native session ID; P4 interrupts cleanly and leaves recoverable state; `stop` terminates owned processes without errors.
- **G3 (A2/B2 Interactive Web Functional Gate)**: Browser opens the bound native session ID, browser and API prompts alternate cleanly on that session, `ready_only` API submission refuses while a browser turn is active, and `interrupt`/`stop` preserve history without replaying prompts.
- **G4 (Teardown Gate)**: Every agent, gateway process, and tmux session on `-L houmao-30-iter1` is stopped cleanly, and user sessions on the default tmux server remain unchanged.

## Measurements and Decision Rules

- **Per-step observation record**: For every arm and checkpoint, record exact commands, exit codes, wall-clock duration, observed tmux pane/Web UI behavior, `houmao-mgr agents single ... state` fields, `GET /v1/usage` output (noting any auth prompt or `401` behavior), and the human reviewer's verdict (`Works as designed`, `Works with caveats / UX friction`, or `Needs revision`).
- **Decision rules**:
  - If `A1`/`A2` pass while `B1`/`B2` fail on `pi-ai/openai-completions` with Qwen 3.8, isolate whether the root cause lies in `dsh-setup.yaml` metadata, `pi-ai` request/tool-call payload expectations, or Qwen 3.8 SGLang server configuration, and open a discussion note before blaming Houmao runtime code.
  - If `houmao-mgr` or `fixture.py` fails on `/v1/usage` or live inspection due to `3.0.0rc1` SSHSIG gateway auth (`#84`), record the exact HTTP status and UX impact as a `3.0.0rc1` integration finding rather than bypassing auth silently.

## Execution Checklist

- [ ] Confirm active self-hosted Qwen 3.8 endpoint URL, model ID, `max_output_tokens`, and reasoning preset (plus DeepSeek `cloud-api` model choice and human watch preference for `dsh_web`)
- [ ] Run G0 prerequisite and isolated-tmux safety check (`-L houmao-30-iter1`)
- [ ] Run Arm A0 (setup diagnostics probe) and record G1 review notes
- [ ] Run Arm A1 (`dsh_acp` on DeepSeek API) step-by-step with human watch pauses
- [ ] Run Arm A2 (`dsh_web` on DeepSeek API) step-by-step with human watch pauses
- [ ] Run Arm B1 (`dsh_acp` on self-hosted Qwen 3.8) step-by-step with human watch pauses
- [ ] Run Arm B2 (`dsh_web` on self-hosted Qwen 3.8) step-by-step with human watch pauses
- [ ] Run Arm C1 (`fixture.py` cross-check)
- [ ] Write dated observation records under `evidences/` and any findings under `discussions/`
- [ ] Verify G4 teardown and update [KQ-1](../key-questions/KQ-1-dsh-basic-functionality.md) and [debug-intent.md](../debug-intent.md)

## Result

Partially executed on `3.0.0rc2`; incomplete and superseded for RC3. The fresh B1 Qwen ACP setup and launch passed, as did P1, a local `hello` turn, and a signed gateway prompt. The first gateway CLI submission was refused because it did not select the enrolled admin signer; an explicit admin `GatewayClient` binding completed the gateway check. P1 usage was recorded and the final observed gateway state was healthy.

The earlier `tmp/houmao-30-iter1/` overlay also failed setup because it still used removed `launch.metadata.tool_params` configuration. That state was preserved and the successful run used fresh RC2 roots.

P2 tool execution, P3 exact continuation, P4 interruption, A1, A2, B2, C1, and G4 teardown were not completed. The RC2 B1 agent was left running at the end of that session. These observations are recorded in the [B1 RC2 log](../logs/2026-11-19-b1-rc2-qwen38-launch-and-gateway-prompt.md); they are not RC3 pass results. Continue with [Iteration 2](2026-11-19-plan-2-dsh-rc3-run-modes.md).
