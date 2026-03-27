## 1. Gateway Prompt-Control Core

- [x] 1.1 Add `GatewayPromptControlRequestV1` and `GatewayPromptControlResultV1` models plus direct gateway client/server wiring for `POST /v1/control/prompt`.
- [x] 1.2 Implement prompt-readiness evaluation for TUI-backed gateways using gateway-owned tracked TUI state, including `force` override and explicit refusal reasons.
- [x] 1.3 Implement immediate prompt-control execution for native tmux-backed headless gateways so prompt work only starts when no active execution is already running.
- [x] 1.4 Keep queued `/v1/requests` semantics intact while ensuring direct prompt control and raw `send-keys` stay distinct execution paths.
- [x] 1.5 Reject `codex_app_server` prompt control explicitly as unsupported.

## 2. Pair And CLI Surfaces

- [x] 2.1 Add `houmao-server` managed-agent proxy support for `POST /houmao/agents/{agent_ref}/gateway/control/prompt`.
- [x] 2.2 Add `houmao-passive-server` proxy support for `POST /houmao/agents/{agent_ref}/gateway/control/prompt`.
- [x] 2.3 Switch `houmao-mgr agents gateway prompt` to the new prompt-control route and add the `--force` flag.
- [x] 2.4 Add structured JSON success output plus structured JSON refusal output with non-zero exit handling for `houmao-mgr agents gateway prompt`.
- [x] 2.5 Ensure `houmao-mgr agents gateway send-keys` still forwards raw control input without prompt-readiness or busy gating.

## 3. Docs And Validation

- [x] 3.1 Update gateway, CLI, pair API, and workflow docs to describe direct prompt-control behavior and remove `request_id`/`queue_depth` expectations from `gateway prompt`.
- [x] 3.2 Add or update unit coverage for prompt-ready dispatch, prompt-not-ready refusal, `--force` bypass, raw `send-keys` during busy posture, and explicit unsupported-backend handling.
- [x] 3.3 Add or update integration/workflow coverage for local and proxied prompt-control routes, including headless overlap refusal and passive-server prompt-control proxying.
