# Implementation and Verification

## Review After Change 05

The Codex adapter replaces the retired controller-owned client and uses the same persistent service owner as DSH and Kimi. The local source is `0910087`. The selected installed native build is Codex CLI `0.169.0`. Its JSON-RPC frames omit the `jsonrpc` field and its initialization response supplies the private `codexHome` and client version. The bounded connection applies separate frame rules for Codex and ACP.

Codex can steer existing work if it receives `turn/start` on a busy thread. Managed input requires an idle bound thread, a current owner reservation, and a final authorization check at write. The correlated return supplies a native handle. Matching item identities and a native terminal notification establish the result. Interruption targets the captured thread and turn. The retired process-ID manifest shape has no current service authority.

An exact cold resume checks the original private rollout and workspace. The adapter restores the saved thread without importing arbitrary history or overriding its working directory. The public control API keeps the private stdio endpoint, process binding, and raw diagnostics inside the owner context.

## Selected Qwen Route and Existing Modes

A direct request to `http://127.0.0.1:14888/v1/responses` with `Qwen/Qwen3.8-27B-FP8` completed and returned usage. The managed fixture used the same exact model and Responses route, a 262,144-token context, and an 8,192-token output selection.

The existing Codex modes ran through the manager on private fixture servers. Run `self-hosted-codex-headless-manager-910186875f0e` selected `headless` and `codex_headless`. Run `self-hosted-codex-tui-manager-208f25e3df93` selected `tui` and `local_interactive`. Each installed `0.169.0` native rollout recorded the requested assistant marker and matching terminal event. Both fixtures stopped their exact owner.

## Accounting

The installed build writes per-response `token_usage_record` lines before the native rollout's `task_complete` event. The reader verifies the process, incarnation, request, thread, workspace and native turn, then uses only individual response records inside that turn. Thread totals and historical or unrelated rows do not contribute. Accounting retries if the native settlement arrived before the rollout flush. The 60 focused usage tests passed.

The first native service run completed two managed Qwen prompts and an exact interrupt on the same process. It reached an accounting assertion before the parser version list recognized `0.169.0`. The new version entry followed inspection of the real rollout shape and the focused accounting regression then passed. Scoped cleanup stopped the initial fixture.

## Live Native Service

Fixture `self-hosted-codex-service-manager-3c886087d753` verified native PID `4063228` with birth `proc:207350386`, service incarnation `0f7be72155ed4c858bd5539930c6c9f6`, and thread `01a1f2c9-2cd0-70c2-b9a5-b4b235e68623`. A separate manager process and a signed gateway caller completed different turns on that same thread and process. The busy service refused a competing prompt. Manager interrupt settled operation `turn-c0b5026a65fb` for the original active native turn without stopping the child.

After gateway detach and reattach, the same service retained the interrupted outcome. A signed AG-UI run returned the exact assistant text and `RUN_FINISHED`. The signed gateway and passive usage paths exposed the same four request records. All three completed turns had positive exact output tokens. The interrupted turn had its own outcome. A new owner and generation then resumed the exact native thread and the model recalled its prior AG-UI answer. The final scoped cleanup returned `stopped_owned_identity`.

The final native rerun after the rollout-offset change used `self-hosted-codex-service-manager-f324eeb85fe0`. It passed the same manager, gateway, exact interrupt, passive, AG-UI, and cold-resume checks. The new incarnation retained thread `01a1f2cb-ce8d-7bf3-80c1-f00ac39c6b0e` and its prior answer. Fixture cleanup succeeded.

## Regression Results

The initial combined integration batch exposed old usage fixtures that instantiated an incomplete fake gateway or lacked the current passive access policy. The repaired accounting integration used a real gateway runtime and signed fixture clients. All 15 cases passed. The HTTPS proxy test failed under the mixed parallel batch and passed in isolation. [Gateway and accounting checks](gateway.md).

The focused launch and persistence tests passed 162 cases. The native provider and ACP regression passed 88. Initial full-unit collection selected a retired Codex client test and a registry test whose fixture chose the first policy by array order. The maintained provider tests and explicit policy selection replaced those assumptions. Ruff, strict mypy, the documentation build, and whitespace checks passed. [Launch checks](launch.md), [provider checks](native-provider.md).

Final Pixi unit verification passed 4,922 tests with 14 skips. The affected integration batch passed 38 with one skip, and the isolated HTTPS proxy test passed separately.
