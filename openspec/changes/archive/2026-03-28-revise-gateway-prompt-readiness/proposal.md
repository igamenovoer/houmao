## Why

`houmao-mgr agents gateway prompt` currently returns queue acceptance before the system knows whether the prompt was actually dispatched to the live agent surface. That prevents the CLI from honestly enforcing "send only when ready" semantics, returning a JSON result that says whether the prompt was sent, and exiting non-zero when prompt delivery is refused.

## What Changes

- **BREAKING** Redefine gateway prompt submission from queued request acceptance to immediate live prompt control that either dispatches the prompt now or rejects it now.
- Add explicit readiness-gated prompt semantics for gateway-managed TUI and headless targets, with `--force` bypassing readiness checks but not bypassing unavailable or unsupported-target failures.
- Keep gateway raw `send-keys` as a separate direct control surface that delivers input immediately and does not apply busy or prompt-readiness gating.
- Add a dedicated managed-agent gateway prompt-control route so `houmao-server` and `houmao-passive-server` can proxy the same immediate dispatch semantics without preserving the old queued `request_id` contract for this command.
- Document that `codex_app_server` is not supported for gateway prompt control yet and must fail explicitly instead of pretending readiness can be evaluated there.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: gateway prompt admission changes from queued acceptance to immediate readiness-gated dispatch, while raw `send-keys` remains direct control input.
- `houmao-srv-ctrl-native-cli`: `houmao-mgr agents gateway prompt` gains direct JSON send-result semantics, readiness refusal errors, and `--force`; `send-keys` keeps direct delivery semantics.
- `houmao-server-agent-api`: managed-agent gateway prompt control changes from queued request proxying to direct prompt-control proxying with immediate success or refusal payloads.
- `passive-server-gateway-proxy`: passive gateway prompt proxying changes to the same immediate prompt-control contract used by the live gateway and pair server.

## Impact

- Affected code: gateway CLI commands, gateway client/service/runtime adapters, managed-agent server proxy routes, passive-server proxy routes, and gateway response models.
- Affected behavior: `agents gateway prompt` no longer returns queue acceptance metadata such as `request_id` or `queue_depth`; callers receive direct send/refusal results instead.
- Affected docs/tests: gateway CLI docs, gateway protocol docs, pair API docs, and workflow coverage that currently expects queued prompt acceptance.
