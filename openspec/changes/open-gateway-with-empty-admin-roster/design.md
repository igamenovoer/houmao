# Design

## Context

The gateway and selected-agent passive ingress share `GatewayAccessPolicy`. It already issues a target- and revision-bound anonymous grant for ordinary admin routes. Web entry and owner-local mail attachments apply additional role checks. See the [proposal](proposal.md) for the intended behavior. [Access policy](../../../src/houmao/gateway/access.py) · [Passive admission](../../../src/houmao/passive_server/admission.py) · [Gateway routes](../../../src/houmao/agents/realm_controller/gateway_service.py)

## Goals and Boundaries

Use the current retained roster for unsigned admission across public-facing access paths to the selected agent. Preserve the scope of each listener, route, mailbox binding, native execution, and plugin service identity. The existing possession challenge controls first-key enrollment. Internal backing operations continue to require their service authority.

## Decisions

### Apply the Live Roster to Both Protected Route Classes

Extend unsigned admission in the shared policy to both private and admin routes when the loaded roster is valid and empty. Retain anonymous provenance and the existing target and revision in each grant. Required policy that fails to load returns a safe HTTP 503. Keep request-bound verification for supplied proofs and the current signed-self and enrolled-admin rules.

Use the same current-grant check for owner-local mail attachment forms. Recognize the anonymous grant from a valid empty revision alongside the existing enrolled-admin grant. Evaluate that authority before opening files or dispatching mail. Mailbox and attachment validation still controls the effect. A separate access flag would require another source of owner policy for the same operation.

### Preserve Caller Provenance Through the Passive Server

Apply the shared rule after resolving the current selected-agent target. When the passive server acts directly, check the anonymous grant against live policy before the operation takes effect. When it forwards, send the anonymous request unsigned so the selected gateway checks the current roster independently. Signed requests continue to use scoped relay proof and keep their caller role. Reusing a service credential for forwarding would obscure who requested the operation. [Passive admission](../../../src/houmao/passive_server/admission.py) · [Gateway client selection](../../../src/houmao/passive_server/service.py)

### Redirect a Bare Browser Request in Open Mode

At the owner-local `GET /v1/web/enter`, check the live policy before handling a bare request. Capture a current anonymous grant and resolve the existing owned Web execution. Recheck the grant after native lookup and return HTTP 302 directly to the verified native destination. This skips both the Houmao login page and ticket issuance for the bare URL. A keyed roster serves the existing interactive signing flow. If the policy becomes unavailable or the selected execution changes, refuse the redirect with a safe diagnostic.

The existing origin check and native destination resolver govern both DSH and Kimi. Keep `Cache-Control: no-store` and `Referrer-Policy: no-referrer` on all Web entry responses. A separate open-entry URL would give operators another endpoint to choose when the same URL can select the live policy. [Web entry](../../../src/houmao/agents/realm_controller/gateway_web_entry.py) · [Native destination resolver](../../../src/houmao/agents/realm_controller/gateway_service.py)

### Normalize the Key Path Before Building the Command

Trim the optional path in the browser's signing-command generator before selecting a signer or classifying an absolute or relative path. Treat a whitespace-only result as SSH-agent selection. Quote the normalized path with the existing shell-quoting function and preserve its interior characters. The field treats surrounding whitespace as input padding. A key whose filename ends in whitespace can be offered through the SSH agent. [Command generator](../../../src/houmao/gateway/_web_login.js) · [Issue #89](https://github.com/igamenovoer/houmao/issues/89)

### Keep the Same Ticket Result for the Manager

Allow unsigned ticket requests on the same direct owner-local route when live admission returns an anonymous grant. Keep direct enrolled-admin proof for keyed issuance. Self, relay, and backing proof remain outside the ticket route's accepted authority. Bind anonymous tickets to the current grant, listener, and verified execution. Revalidate the grant and native binding at redemption, including after resolving the native redirect. First enrollment invalidates an outstanding anonymous ticket even if final-key removal later reopens the gateway.

The manager checks a fresh owner-local endpoint descriptor against the selected execution and listener. The pair `admin_access: open` and `private_proof: none` selects an unsigned ticket request. Keyed policy selects the configured enrolled signer. The gateway makes the final admission decision, and a refusal ends the attempt. This preserves the existing `url` and `expires_at_utc` result and 60-second single-use behavior. Returning the bare URL from the manager would remove the bounded handoff that existing callers request through this command. [Manager command](../../../src/houmao/srv_ctrl/commands/managed_agents.py) · [Gateway client](../../../src/houmao/agents/realm_controller/gateway_client.py)

### Publish Effective Proof Requirements

Emit `private_proof` as `none` for open policy, `self_or_admin` for keyed policy, and `unavailable` for unavailable policy. Update the registry v5 schema with the same values. Keep `self_or_admin` as the model default for older records that omit the field. Cached discovery serves as a locator and clients verify the current owner-local endpoint before selecting unsigned Web ticket issuance. A separate descriptor version would require a schema migration for an additive value set. [Endpoint descriptor](../../../src/houmao/gateway/deployment.py) · [Registry schema](../../../src/houmao/agents/realm_controller/schemas/managed_agent_registry_record.v5.schema.json)

## Risks and Trade-Offs

- Enrollment can occur during Web lookup or passive forwarding. Check authority again at the redirect or downstream admission boundary. Native browser sessions already established continue under the provider's credential lifetime.
- An updated gateway with an empty roster exposes its enabled operations to reachable callers. Existing listener configuration and route enablement define reachability. Enroll a key before upgrading a deployment whose callers should remain subject to proof requirements.

## Migration Plan

Use the existing roster and launch manifest formats. Restart running gateways on the updated version to load the new admission behavior. Update consumers that strictly parse the endpoint descriptor along with the gateway. Older readers accept only the previous private-proof value. Before rolling back, detach the upgraded gateway to clear its published descriptor, then start the older version with the retained roster. First-key enrollment and final-key removal change new admission decisions live.
