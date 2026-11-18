# Proposal

## Why

[Issue #84](https://github.com/igamenovoer/houmao/issues/84), active roadmap item 10, requires an external hub to reach an agent across Linux-user, container, and host boundaries without shared files or trusted-localhost assumptions. Execution ownership is established by #81; the remaining boundary is authenticated, operation-authorized access to that owner's gateway, mailbox, and plugins.

## What Changes

- Add explicit authenticated gateway deployment with externally provisioned opaque bearer credentials, owner-bound private verification policy, fixed `peer` and `operator` authority, and live credential rotation. Keep the default gateway on loopback and document a supported HTTPS reverse-proxy deployment.
- Add `POST /v1/messages` for ordinary literal notifications through the existing immediate event-dispatch machinery. Reserve queued requests, direct prompt control, interruption, raw keys, session selection, scheduling, native refresh, memory, and AG-UI for operators in authenticated mode.
- Separate listener binding, owner-local connection, and advertised remote endpoint metadata. Extend the shared HTTP client with explicit endpoint-bound private credentials, HTTPS verification, and redirect refusal; preserve direct-by-default proxy handling.
- Enable remote offline/online mailbox and ordinary plugin operations only behind the authenticated boundary. Replace the mailbox, plugin-activation, and event-dispatch loopback checks with one access policy, retaining owner, binding, readiness, and incarnation checks.
- Close alternate HTTP paths to protected agents, including passive-server proxies and direct headless, observation, interrupt, and stop paths. Authorize necessary owner-side backing calls explicitly. Remote passive-server deployment and its global launch, discovery, and administration APIs remain outside this change.
- **BREAKING:** Reject unauthenticated broader gateway binds. Tokenless consumers of an explicitly protected agent receive authentication failures and must use a configured client binding; they cannot fall back to another transport. Update affected strict metadata schemas and repository consumers together without legacy migration shims.

## Capabilities

### New Capabilities

- `authenticated-gateway-access`: Explicit deployment, owner-bound caller authentication and authorization, private credentials and rotation, remote client safety, and protection against alternate-ingress bypasses.

### Modified Capabilities

- `agent-gateway`: Authenticated listener policy, ordinary message delivery, remote mailbox availability, and explicit connect/advertised endpoint behavior.
- `gateway-plugin-api`: Host-enforced route access declarations and authenticated remote plugin operations with preserved owner-bound ordinary dispatch.
- `agent-discovery-registry`: Secret-free, context-qualified advertised gateway descriptors that remain locators rather than credentials or lifecycle grants.
- `per-agent-ag-ui-attachment`: Operator authorization and bounded stream revocation without agent lifecycle effects.
- `passive-server-gateway-proxy`: Preserve authentication failures and prevent credential substitution or direct-control bypass for protected targets.

## Impact

Product work touches `src/houmao/gateway/`, realm-controller gateway models/service/client/storage/runtime, registry schema producers and readers, the scoped gateway CLI, owner-side executor attach dispatch, selected-agent passive-server boundaries, and the maintained backing HTTP client. CCCC and the independent plugin example gain explicit route classifications. Reuse FastAPI, Pydantic, standard-library cryptographic primitives, existing private-file conventions, and immediate dispatch; add no authentication framework, identity database, or retry queue.

CI belongs in existing gateway, plugin, passive-server, and execution test trees. Update gateway protocol, deployment, plugin, mailbox, registry, and CLI references, provide a reproducible TLS qualification procedure, and record #84 acceptance evidence before marking the roadmap complete.
