# Proposal

## Why

Managed Web agents publish a clean native origin, but a fresh browser still needs the provider's sign-in parameters. [Issue #88](https://github.com/igamenovoer/houmao/issues/88) documents how DSH operators currently retrieve private fixture state to authenticate.

## What Changes

- Use `GET /v1/web/enter` for interactive and automated entry. Without a ticket, it shows a login page. A valid ticket sends the browser directly to the native sign-in destination.
- Offer a copyable terminal command that signs a browser login challenge and submits the proof with `curl`. The admin can enter a local key path or leave it blank to use the available SSH agent keys. The initiating tab continues automatically after approval.
- Require proof from an enrolled administrator for both interactive login and signed API ticket issuance, including gateways with an empty admin roster. Both flows issue the same short-lived, single-use entry ticket for the verified Web execution.
- Redirect the browser to a verified, backend-owned native sign-in destination. DSH uses a query parameter to establish its native cookie. Kimi uses a URL fragment for native authentication.
- Add `houmao-mgr agents single --agent-id <id> gateway web-entry` for operators. The command returns the ticket URL and its expiry. Discovery continues to report the clean native origin and bound session identity.
- Support browsers and terminal callbacks on the owner's loopback or explicitly arranged private TCP tunnels that preserve the required addresses.
- Invalidate pending logins and outstanding tickets on expiry, gateway replacement, or a change to the bound native execution or approving administrator. Key files stay on the admin's machine. Keep proof, tickets, and native credentials out of normal state and diagnostic output.

## Capabilities

### New Capabilities

- `gateway-web-entry` defines the shared entry URL, interactive browser login, one-time tickets, and private native browser destinations.

### Modified Capabilities

- `authenticated-gateway-access` requires enrolled admin proof for direct issuance and interactive login, each scoped to its operation.
- `dsh-web-control` exposes the qualified native browser sign-in path to the owning gateway.
- `kimi-web-control` exposes the verified native fragment sign-in path to the owning gateway.
- `houmao-srv-ctrl-native-cli` adds the scoped gateway browser entry command.
- `agent-gateway-reference-docs` documents terminal-assisted browser sign-in, signed automation, the ticket lifetime, and the loopback boundary.

## Impact

The gateway gains a login page and HTTP operations for browser approval, ticket issuance, and redemption. The managed Web adapters supply private browser destinations, and the manager gains a scoped command using its signed gateway client. Browser regressions will exercise terminal approval and both native authentication paths. The entry flow uses the existing gateway and native listeners.
