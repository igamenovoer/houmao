# Implementation and Verification

## Review After Change 04

Kimi uses the shared service owner, exact request authority, and private caller channel implemented in 04. Its native ACP session checks are separate from DSH. The local Kimi source at `67325c1` served as the protocol reference. Live qualification selects the installed Kimi Code `2.6.0` separately.

Kimi restores existing sessions by native ID, and its ACP resume response omits the ID. The design requires workspace-bound evidence in the selected private home before resume. It also separates the irreversible write to the owned stdio channel from the native journal's proof that a turn started and settled. Native failure and local commands can both return ACP `end_turn`. Kimi's untagged update stream can include restored history and context occupancy, so a correlated reply alone cannot settle or charge a managed request.

Live testing uses the explicit `self-hosted` fixture case, `Qwen/Qwen3.8-27B-FP8`, the local Chat Completions route, a 262,144-token context, and an 8,192-token maximum output. Fixture lifecycle and native artifacts stay outside the checkout, and tmux uses exact private sockets.

## Existing Kimi Modes

Two fresh manager fixtures used the installed `2.6.0` binary with the same self-hosted Qwen route. Run `self-hosted-kimi-headless-manager-4e15d02e5d5f` selected `headless` and `kimi_headless`. Run `self-hosted-kimi-tui-manager-1413ec0554c9` selected `tui` and `local_interactive`. Each native journal contained the requested assistant text. Both fixtures reported `stopped_owned_identity`.

## Accounting

Usage reads the exact certified byte interval in the main Kimi wire journal. It checks the request, process birth, service incarnation, session, turn, prompt and journal identity. The owner supplies the immutable terminal receipt and existing accounting artifacts. The focused usage suite passed 59 checks, including reconstruction after the recording process exits, rejection of a stale incarnation, and exclusion of before-boundary history, context occupancy, and after-boundary usage.

## Live Kimi ACP

The installed binary negotiated ACP protocol `1`, selected its configured model, and confirmed native `auto` posture. One live lane established native process `4007139` with birth `proc:207295672`, incarnation `d1b3301ee21b45a6a7faff1c97292246` and native conversation `session_7f3a1f71-de56-418b-b0ca-f038a6521bb6`. The external fixture is `self-hosted-kimi-service-manager-cfc69a85b78b`.

The direct manager and signed gateway requests settled as native turns `0` and `1` in that process. A passive observer reported the same service ready. A busy plugin wake received HTTP 409 without sending input. The next wake settled as native turn `2` and remained readable after gateway reattach. The signed AG-UI run streamed attributable assistant output and `RUN_FINISHED` for native turn `3`. The signed gateway ledger returned four distinct, positively measured request records. After owner stop and exact cold relaunch, the generation and incarnation changed while the native conversation stayed the same. The next request settled as native turn `4`, and scoped cleanup succeeded.

The initial end-to-end script used the wrong field for the passive mode assertion. It stopped and cleaned up after its two native prompts. The passing lane read the mode from the public capability projection.

A third private lane, `self-hosted-kimi-service-manager-875ed700e713`, verified that a signed passive `/usage` request forwarded the same four exact records. After cold resume, the model repeated the previous AG-UI answer when asked to recall its last reply. The test prompt did not include that answer. This lane also stopped its private service and supervisor.

## Regression Results

The affected DSH service, gateway, Kimi headless, registry and AG-UI integration batch passed all 25 cases. The Kimi launch and service owner suite passed 156 focused cases. A separate Kimi headless and TUI batch passed 44. The full Pixi unit suite passed 4,892 cases with 14 skips. Ruff, strict mypy, the documentation build, and whitespace checks passed. [Gateway and projection checks](gateway.md).
