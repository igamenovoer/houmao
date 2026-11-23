# KQ-1: DSH Basic Functionality With Houmao

Date: 2026-11-18. Updated: 2026-11-20. Status: KQ-1.2 answered for the RC3 Qwen lane with revision needed; the full question remains unresolved. The active live pass uses rc5; the DeepSeek lane is deferred as of 2026-11-20. Owners: [iteration 1](../iterations/2026-11-18-plan-1-dsh-basic-functionality.md) (historical) and [iteration 2](../iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md) (current). Evidence: [B1 RC2 launch and gateway prompt](../logs/2026-11-19-b1-rc2-qwen38-launch-and-gateway-prompt.md), [RC3 H1 preparation](../evidences/2026-11-19-rc3-iteration2-g0-and-h1-preparation.md), and [RC3 H1 results](../logs/2026-11-19-h1-rc3-headless-execution.md).

Does Houmao prepare, launch, observe, control, resume, interrupt, account usage for, and stop DeepSeek Harness cleanly across its qualified run modes under live human observation on the DeepSeek API (`cloud-api`) and self-hosted Qwen 3.8 (`self-hosted`) model lanes? The current target is Houmao `3.0.0rc3` with DSH `0.2.2-rc.3`: `headless` uses one native CLI worker per prompt, `service` keeps one ACP process alive, and `web` shares a native conversation between browser and API clients.

## Critical Propositions

### KQ-1.1: Operator Setup, Mode Selection, and Executable Resolution UX

A human operator creating a fresh disposable project overlay can select each DSH run mode explicitly through `project profile create --mode` and `project agents launch --mode`. Validation identifies unsupported tool/mode pairs before launch, retains the selected mode in runtime identity, and gives fresh-launch guidance for retained RC2 schemas. DSH `0.2.2-rc.3` is selected explicitly; no ambient executable or credential fallback is accepted.

- **Test criteria**: Exercise fresh project setup, stored and direct mode selection, DSH's default `web` mode, rejection of DSH `tui`, empty model and missing credential diagnostics, and a read-only probe of retained RC2 metadata in Iteration 2 Arm R0.

### KQ-1.2: Native One-Shot Headless Lifecycle and Exact Continuation

A `dsh_headless` launch preserves the managed identity while each accepted prompt creates exactly one native worker. Successive prompts use different worker processes but resume the same exact native session. Interruption targets only the active worker, and native handoff, terminal outcome, and process closure remain distinguishable.

- **Test criteria**: Complete P1 through P4 in Arms H1 and H2; compare worker and native session identities across prompts; inspect native JSON, canonical events, and finalized usage; verify unsupported terminal input fails explicitly and next-invocation home refresh does not create a worker.

### KQ-1.3: Persistent ACP Service Lifecycle and Unified Owner Control

A `dsh_acp` service keeps one native process, service incarnation, and logical session across independent manager and authenticated gateway prompts. Gateway detach or client loss does not stop the provider or replay work. Exact relaunch creates a new service incarnation while preserving the selected native conversation, and startup-bound native-home changes apply only at the documented boundary.

- **Test criteria**: Complete P1 through P4 in Arms S1 and S2; compare manager and signed-gateway admission; detach and reattach during active work; verify busy refusal, interruption, usage continuity, exact stop/relaunch, and native-home refresh behavior.

### KQ-1.4: Interactive Web Lifecycle and Human/API Coexistence

A `dsh_web` launch publishes a safe browser origin and exact native session without exposing private sign-in material in public state. A human can use the browser alongside manager and authenticated gateway prompts, with truthful busy admission, interruption, gateway reattachment, and history preservation.

- **Test criteria**: Exercise browser observation, human-versus-API turn alternation, busy `ready_only` refusal, interruption, detach/reattach, exact relaunch where supported, and stop in Arms W1 and W2.

### KQ-1.5: Provider Parity, Passive Recovery, and Usage/Auth Observability

Both selected provider lanes complete basic turns, tool calls, exact continuation, and usage accounting. Unsigned private gateway routes remain rejected, while enrolled admin proof succeeds. Passive-server restart reconstructs an active native headless turn without replay and exposes its original turn identity, canonical events, raw stdout artifact, and finalized usage.

- **Test criteria**: Compare Qwen and DeepSeek results across corresponding arms; run Arm V1 for passive recovery and Arm C1 for maintained fixture ergonomics. Compare usage with native journals and ensure each accepted request creates at most one native admission.

## Answer

Partial RC2 evidence answered only a narrow predecessor of KQ-1.3 and KQ-1.5. On 2026-11-19, a fresh Houmao `3.0.0rc2` Qwen ACP agent completed P1 and a local `hello` turn. A signed gateway prompt also completed after the campaign's unsigned CLI route was refused and an enrolled admin binding was supplied explicitly. The gateway was healthy at the final check, and usage recorded P1. P2 tool execution, P3 exact continuation, P4 interruption, DeepSeek, Web, and teardown were not completed. That evidence does not qualify RC3 native headless workers or the RC3 persistent-service lifecycle.

RC3 H1 completed on the Qwen lane from physical checkout `tmp/` storage. P1–P4 verified literal preservation, tool execution, exact native-session continuation through different workers, interruption with partial finalized usage, and clean teardown. Reasoning level 1 selected native `low`, provider reasoning and progress appeared in durable artifacts during execution, a newly added skill loaded on the next invocation, and unsupported `send-keys` and ACP-only MCP declarations failed explicitly. H1 nevertheless **Needs revision**: `turn events --detail detail` rejects whitespace-only assistant events with a `HoumaoHeadlessTurnEvent.message` validation error, and the supervisor pane showed no live output. Thus KQ-1.2 has a Qwen-lane answer with a concrete observability defect, while H2 has not run.

KQ-1 remains unresolved for RC3 service, Web, passive recovery, fixture/auth ergonomics, and remaining setup checks; the DeepSeek lanes are deferred as of 2026-11-20. The other Iteration 2 gates still need to be executed and recorded.

## Scope

This question covers DSH setup, `headless`, `service`, and `web` lifecycle, operator and gateway control, live human watchability, passive headless recovery, and usage/auth observability. Cross-user execution-owner routing, mailbox and CCCC coordination, and non-DSH providers belong to other campaign questions. Kimi ACP/Web, Codex app-server, and cross-tool TUI/mode persistence require a separate RC3 follow-on question; that follow-on is deferred as of 2026-11-20. Passing DSH alone does not qualify the full RC3 run-mode implementation.
