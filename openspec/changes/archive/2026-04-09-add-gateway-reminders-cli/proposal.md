## Why

Gateway reminders are currently exposed only through direct live `/v1/reminders` HTTP, while nearby gateway features such as prompt control and mail-notifier already have first-class `houmao-mgr agents gateway ...` commands and pair-managed proxy surfaces. That mismatch makes reminder operations harder to automate, harder to teach through Houmao-owned skills, and inconsistent across local and pair-managed operator workflows.

## What Changes

- Add a native `houmao-mgr agents gateway reminders ...` command family for inspecting and mutating live gateway reminders through managed-agent selectors instead of requiring direct raw gateway URLs.
- Support reminder inspection and mutation subcommands that fit existing Houmao CLI conventions: `list`, `get`, `create`, `set`, and `remove`.
- Add ranking controls that keep ranking numeric while also supporting convenience placement flags for “add before all current reminders” and “add after all current reminders”.
- Add pair-managed reminder proxy routes so `--pair-port` and other server-backed `agents gateway` targeting modes can work for reminder operations with the same contract as other gateway control features.
- Update Houmao-owned gateway skill guidance and operator/reference docs so reminders are taught as a supported CLI surface first, with direct `/v1/reminders` remaining the low-level contract underneath.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: extend `houmao-mgr agents gateway` with a native `reminders` subgroup, managed-agent targeting parity, and ranking placement convenience flags.
- `passive-server-gateway-proxy`: add managed-agent gateway reminder proxy routes so pair-managed reminder operations do not require direct live gateway addressing.
- `houmao-agent-gateway-skill`: update reminder routing and examples so the packaged skill points callers at the supported CLI and managed-agent proxy surfaces before low-level direct HTTP.
- `docs-cli-reference`: document the new `agents gateway reminders` family, options, selector rules, and ranking placement behavior in the CLI reference.
- `agent-gateway-reference-docs`: update gateway reminder reference pages to describe the new CLI and managed-agent proxy surfaces while preserving the direct `/v1/reminders` contract as the underlying live gateway API.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/agents/gateway.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, `src/houmao/server/app.py`, `src/houmao/server/service.py`, `src/houmao/server/client.py`, `src/houmao/server/pair_client.py`, gateway renderers, and related tests.
- Affected docs and skill assets: `docs/reference/cli/agents-gateway.md`, `docs/reference/cli/houmao-passive-server.md`, `docs/reference/gateway/operations/reminders.md`, and `src/houmao/agents/assets/system_skills/houmao-agent-gateway/`.
- API impact: new managed-agent `/houmao/agents/{agent_ref}/gateway/reminders...` proxy routes, while direct `/v1/reminders` remains supported.
