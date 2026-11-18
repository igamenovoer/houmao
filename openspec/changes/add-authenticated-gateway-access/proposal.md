# Proposal

## Why

[Issue #84](https://github.com/igamenovoer/houmao/issues/84) calls for a hub to reach an agent across Linux-user, container, and host boundaries. With execution ownership established by #81, the gateway needs explicit public contact, private access for the agent, and owner-bound admin access.

## What Changes

- Classify routes as `public`, `private`, or `admin`. Private routes require a signature from the current `self` key or a listed admin key. Admin routes are open while the valid admin key list is empty, and require a listed key once it contains entries.
- Accept zero or more initial admin public keys in the owner-authorized launch manifest. Admit admin claims using one-time SSH-key signature challenges over HTTP. A caller can enroll the first key after startup by proving possession, and current admins can add or remove keys live. The final removal reopens admin routes.
- Add public `POST /v1/messages` notifications and `POST /v1/public/prompt` requests. The gateway wraps the input with public provenance and instructions to follow existing agent policy. HTTP reports handoff only. A caller who wants an answer specifies a separate delivery channel for the agent to use if permitted.
- Retain the live admin list with the agent and execution context. Give each managed generation its own self signing key. Normal `houmao-mgr agents self ...` commands handle challenge and signing automatically, and gateways verify SSHSIG proofs in process with Python. Publish a secret-free endpoint descriptor with current access requirements.
- Keep loopback as the default bind and make remote and public-input exposure explicit. Separate bind, owner-local connect, and advertised addresses. Support verified HTTPS through a reverse proxy, including deployment-provisioned certificate trust, and explicit encrypted tunnels.
- Classify ordinary offline and online mailbox operations, memory, detailed status, usage, and ordinary plugin operations as private. Classify queued and direct control, interruption, raw keys, scheduling, native refresh, key management, and AG-UI as admin.
- Enforce target policy on passive-server proxies and direct selected-agent paths, including after detach. Authorize server-managed backing calls with their own configured credentials. Remote publication covers the per-agent gateway.
- **BREAKING** Private routes require caller proof on every listener. Admin routes use the recorded key list even on loopback. Broader binds require explicit validated access settings. Update strict schemas and callers together so admission refusal ends the request.

## Capabilities

### New Capabilities

- `authenticated-gateway-access` defines route access, generation-bound self proof, admin key enrollment and signed challenges, retained policy, and secure transport.

### Modified Capabilities

- `agent-gateway` defines public one-way input, protected mailbox and control routes, and distinct listener and advertised endpoints.
- `gateway-plugin-api` adds host-enforced route access and preserves owner-bound service event delivery.
- `agent-discovery-registry` publishes secret-free, context-qualified endpoint descriptors with access requirements.
- `per-agent-ag-ui-attachment` applies the current admin access state and bounds stream revocation.
- `passive-server-gateway-proxy` preserves caller authority and protects alternate selected-agent ingress.
- `passive-server-request-submission` requires target admission before prompt, interrupt, stop, or gateway lifecycle handling.
- `agent-mailbox-system-skills` uses bound caller credentials for routine gateway mail operations.
- `agent-gateway-reference-docs` explains the three access classes, public input, and authenticated remote mailbox availability.

## Impact

Product work touches gateway access, service, client, storage, and runtime code. It also affects managed launch and join, scoped CLI and mailbox helpers, executor attach dispatch, registry schemas, and passive-server and backing clients. CCCC and the independent plugin example gain explicit route classifications. Declare `cryptography` as a runtime dependency for in-process key handling and SSHSIG verification.

Extend existing gateway, plugin, passive-server, and execution suites. Update the affected references and qualify the HTTPS deployment and two-user access before recording #84 completion.
