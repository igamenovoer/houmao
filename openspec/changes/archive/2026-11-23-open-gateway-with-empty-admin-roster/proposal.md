# Proposal

## Why

An empty admin roster already opens ordinary gateway control. Detailed inspection, mailbox operations, and Web entry still require proof, which prevents a deliberately keyless agent from being fully usable.

## What Changes

- **BREAKING**. An initialized, valid empty admin roster permits anonymous access to every enabled operation on the selected agent's gateway, including private and admin routes. Selected-agent passive HTTP routes apply the same live policy.
- Opening the bare Web entry URL immediately redirects into the verified live DSH or Kimi Web interface when the roster is empty. A nonempty roster selects the existing interactive signing flow.
- The interactive login form trims surrounding whitespace before interpreting the optional private-key path. An empty result selects the local SSH agent. [Issue #89](https://github.com/igamenovoer/houmao/issues/89)
- The scoped `gateway web-entry` command can request its usual one-time link unsigned when the gateway is open. The link still expires and applies to one live Web execution.
- The first enrolled key closes anonymous access. Final-key removal reopens access. Missing or damaged access state fails closed, and registration continues to prove possession of the proposed key.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `authenticated-gateway-access` defines empty-roster admission for enabled routes and privileged forms.
- `gateway-web-entry` defines immediate anonymous browser entry, revision-bound unsigned tickets, and normalization of the interactive key-path field.
- `houmao-srv-ctrl-native-cli` defines signer selection for the scoped Web entry command.
- `agent-gateway` updates mailbox admission, owner-file inputs, and endpoint descriptors.
- `agent-discovery-registry` describes the effective proof policy in gateway discovery.
- `passive-server-gateway-proxy` preserves anonymous admission through the existing selected-agent proxy and direct operation paths.
- `gateway-plugin-api` applies empty-roster admission to both plugin route classes.
- `dsh-web-control` covers native browser entry from the open gateway.
- `kimi-web-control` covers native browser entry from the open gateway.
- `agent-gateway-reference-docs` covers the access transition and the browser and CLI workflows.

## Impact

The change affects the shared access policy, gateway route handlers and client, passive ingress, endpoint metadata, and operator documentation. Existing deployments that rely on private or Web routes requiring proof must enroll an admin key before exposing the upgraded gateway to callers who should lack access. Listener reachability, native ownership, enabled capabilities, and input validation continue to govern operations.
