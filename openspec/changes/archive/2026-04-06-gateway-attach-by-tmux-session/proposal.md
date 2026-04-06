## Why

`houmao-mgr agents gateway attach` already supports explicit managed-agent selectors and same-session discovery from inside the owning tmux session, but it does not provide a supported explicit path for operators who are outside tmux and only know the target tmux session name. That leaves a gap between the runtime's manifest-backed tmux authority model and the operator-facing attach workflow at exactly the point where attach is often needed for recovery or inspection.

## What Changes

- Add an explicit `--target-tmux-session <tmux-session-name>` selector to `houmao-mgr agents gateway ...` commands that target one managed agent.
- Make gateway attach and related gateway commands resolve that selector through manifest-first tmux-session authority, with shared-registry fallback when the tmux-published manifest pointer is missing or stale.
- Keep existing `--agent-id`, `--agent-name`, and `--current-session` behavior unchanged rather than introducing duplicate agent-selector flags.
- Rename the gateway command family's ambiguous pair-authority override from `--port` to `--pair-port` so operators can distinguish it from the gateway listener port.
- Keep `--pair-port` limited to explicit managed-agent id or name targeting; reject it for tmux-session targeting so the command follows the manifest-declared authority for the addressed live session.
- Add regression coverage and operator documentation for outside-tmux gateway attach by tmux session name.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: Gateway attach and related gateway commands must support explicit outside-tmux targeting by tmux session name in addition to existing explicit agent selectors and current-session targeting.
- `houmao-srv-ctrl-native-cli`: The native `houmao-mgr agents gateway ...` CLI contract must accept `--target-tmux-session` as a mutually exclusive selector and rename the pair-authority override to `--pair-port`.
- `houmao-mgr-registry-discovery`: Local registry-backed discovery for managed-agent post-launch control must expose the tmux-session alias path through an explicit gateway CLI selector rather than leaving it only as internal tooling capability.
- `docs-cli-reference`: CLI reference pages for `houmao-mgr agents gateway` and related selector guidance must document the new tmux-session selector, `--pair-port`, and their targeting rules.
- `agent-gateway-reference-docs`: Gateway operational docs must explain when to use `--target-tmux-session`, how it resolves authority, how it differs from `--current-session`, and how `--pair-port` differs from gateway listener port overrides.

## Impact

- Affected CLI targeting and resolution code in `src/houmao/srv_ctrl/commands/agents/gateway.py`, plus shared managed-agent discovery helpers under `src/houmao/srv_ctrl/commands/`.
- Affected local registry-backed lookup helpers under `src/houmao/agents/realm_controller/registry_storage.py` and manifest-authority resolution paths reused by gateway attach.
- Affected operator documentation for `docs/reference/cli/agents-gateway.md`, `docs/reference/cli.md`, and gateway operational reference pages, including the pair-authority versus gateway-listener port distinction.
- Affected regression coverage for gateway CLI selector validation and outside-tmux attach flows in unit and integration tests.
