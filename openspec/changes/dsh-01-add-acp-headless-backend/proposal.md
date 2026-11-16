# Proposal

## Why

Houmao cannot currently select DeepSeek Harness (DSH) as a managed agent body, although issue [#74](https://github.com/igamenovoer/houmao/issues/74) requires its lifecycle, structured control, and usage accounting. Establish headless ACP support first so interactive Web support can reuse a qualified tool definition, isolated configuration, native prompt injection, and accounting adapter.

## What Changes

- Add tool `dsh` and backend `dsh_acp` to maintained project, credential, model, launch-policy, runtime, gateway, and passive-server headless paths.
- Run an ACP driver through the existing tmux-backed headless turn lifecycle. Create or resume the exact native session, consume semantic updates, cancel active work, and close and flush the native session before ending each process.
- Build isolated DSH homes and profiles with explicit provider routes, endpoint protocols, model metadata, projected skills, MCP/tool configuration, and startup-only HMR behavior. Apply the complete Houmao prompt through a literal native system-prompt section.
- Extend the shared usage ledger with a qualified reader for DSH's uncompressed native session journal, including attempts, retries, native turn boundaries, and explicit unknown or partial measurements.
- Preserve immediate ordinary-message refusal and execution-generation fencing. A failed attempt is never automatically resent after provider or controller failure.
- Extend the two generic fixture cases with DSH headless preparation and qualification. DeepSeek credentials remain local; generic self-hosted routes use an explicitly selected compatible adapter.

## Capabilities

### New Capabilities

- `dsh-headless-control`: ACP session lifecycle, concurrent protocol handling, permissions, outcome mapping, and supported-operation reporting for managed DSH headless agents.

### Modified Capabilities

- `native-cli-provider-support`: Recognize DSH as a maintained tool with explicitly qualified backend capabilities.
- `brain-launch-runtime`: Compose isolated DSH launches, native prompts, configuration provenance, and exact-session continuation through `dsh_acp`.
- `agent-gateway`: Support DSH headless execution and immediate native handoff through the existing gateway contract.
- `agent-usage-records`: Collect provider-faithful DSH journal evidence without treating ACP context occupancy as consumption.
- `passive-server-headless-management`: Launch and recover DSH headless agents through supported passive-server routes.
- `test-agent-launch-fixtures`: Prepare and qualify DSH headless launches using the existing endpoint cases and local secret handling.

## Impact

Implementation affects `src/houmao/agents/`, its packaged assets and runtime schemas, `src/houmao/project/`, `src/houmao/srv_ctrl/`, and `src/houmao/passive_server/`. Development support belongs in `tools/dsh/`, `scripts/qualification/dsh/`, the existing fixture helper, and contributor documentation. Tests belong in the unit and integration suites; credentials and private run artifacts stay outside the checkout.

DSH remains an external, explicitly installed executable. Qualify the source reference `39163dd30f703a79079e2d2446545cff3c453738` and record the corresponding installed version/build identity; the protocol handshake's placeholder version is insufficient. No general backend plugin framework, DSH SDK transport, terminal parser, coordinated live refresh (#82), or remote execution/authentication boundary (#81/#84) is introduced.

This is change **01**, followed by [dsh-02-add-interactive-web-backend](../dsh-02-add-interactive-web-backend/proposal.md). Implement and validate this change before starting 02. The second change owns the user-selected `tui` posture and its Web surface; this first change makes no interactive support claim.
