# Design

## Context

See [proposal.md](proposal.md) for motivation and the six capability deltas for behavior. This design applies the per-agent gateway entry point selected during exploration.

The maintained gateway uses one FastAPI application for core, AG-UI, and staged plugin routes. Its HTTP boundary currently has diagnostic and plugin-lifecycle middleware but no caller authentication. Three separate listener restrictions exist: mailbox operations in [gateway_service.py](../../../src/houmao/agents/realm_controller/gateway_service.py), plugin staging in [gateway_plugin_host.py](../../../src/houmao/agents/realm_controller/gateway_plugin_host.py), and ordinary plugin-event dispatch in the gateway runtime. They must change together.

[GatewayClient](../../../src/houmao/agents/realm_controller/gateway_client.py) constructs HTTP loopback URLs from listener coordinates and does not accept credentials. Gateway state and registry models publish host/port rather than an independent remote URL. [runtime.py](../../../src/houmao/agents/realm_controller/runtime.py) constructs additional clients for live-plugin reuse, readiness, and owner controls; those paths need the same explicit binding.

Existing ordinary plugin delivery already supplies bounded literal envelopes, readiness and incarnation checks, confirmed handoff, and sender-owned retries. Existing queued requests accept both prompts and interrupts, and reminders can deliver raw keys. [Mail attachment inputs](../../../src/houmao/mailbox/models.py) contain owner-local filesystem paths. These surfaces have different authority requirements even when their HTTP methods match.

The passive server has both proxies and direct headless, observation, artifact, interrupt, and stop paths. Direct managed-headless resolution can succeed before registry discovery, and direct stop can terminate tmux and clear registry state. Authenticating only its outbound gateway clients would leave alternate ingress open.

The completed execution-owner contract supplies observed context identity, UID/GID, owner-side runtime authority, and restricted finite dispatch. Its gateway-attach vocabulary in [owner.py](../../../src/houmao/execution/owner.py) and [application.py](../../../src/houmao/execution/application.py) currently accepts only background and timing arguments. Access configuration must enter through that boundary before any owner-side file is opened.

## Goals / Non-Goals

**Goals:** Add one caller-access policy that protects the existing execution boundary, keeps ordinary delivery literal, and can be enforced consistently by gateway and necessary selected-agent backing routes. Keep the implementation within current routing, persistence, dispatch, and diagnostic infrastructure.

**Non-Goals:** Build an identity provider, password scheme, token-issuance service, generic policy language, remote filesystem, attachment-upload protocol, GUI login workflow, or replay journal. Support remote passive-server launch, global discovery, or administration. Add OS security isolation between processes sharing a UID, or remove an administrator's existing owner-side lifecycle authority.

## Decisions

### 1. Use a Small Owner-Bound Access Module

Add a focused product module under `src/houmao/gateway/` for strict access configuration, credential verification, principal/grant values, and the fixed operation policy. Reuse the existing framework and standard-library cryptographic facilities. Do not introduce an authentication provider registry or policy database.

The two deployment modes are `trusted_local` and `authenticated`. The first requires loopback and preserves existing local workflows. The second always requires credentials for protected routes, including requests from loopback. Broader listeners require authenticated mode. Anonymous `GET /health` exposes only process-health and protocol fields.

A validated deployment-policy value replaces all three unconditional loopback checks. It authorizes the deployment posture, while request grants authorize HTTP operations. Background plugin workers retain their existing configured service authority; they do not fabricate HTTP principals.

Alternative considered: authenticate only at a proxy. Requiring gateway verification also protects direct access to the backend port and keeps operation authorization next to the handlers.

### 2. Provision Opaque Credentials Outside the Runtime

Use externally generated secrets with at least 256 bits of entropy. The bearer representation contains a safe credential ID and opaque secret. The selected JSON policy has a version, expected agent ID and context ID, and entries mapping credential ID to principal ID, role, and SHA-256 verifier. Compare fixed-size digests in constant time. Human passwords are not an input to this scheme.

Illustrative policy, with placeholder values:

```json
{
  "schema_version": 1,
  "agent_id": "<bound-agent-id>",
  "context_id": "<observed-owner-context-id>",
  "credentials": [
    {
      "credential_id": "hub-operator-a",
      "principal_id": "hub",
      "role": "operator",
      "verifier_sha256": "<verifier-of-random-secret>"
    }
  ]
}
```

Keep policy, owner-client secrets, and standalone client bindings in explicitly selected regular private files outside the checkout. Enforce observed owner, private permissions, symlink rejection, duplicate-key rejection, and a 1 MiB document ceiling. Reject malformed IDs, roles, digests, and duplicate credential IDs. Reuse suitable parsing/private-file helpers after checking their semantics; the current mailbox helper's path-based stat check alone does not supply the descriptor-based and symlink protections used by the plugin credential reader. Share only small validated primitives if extraction is needed.

Read the bounded policy at each admission. Atomic replacement supports overlapping credentials, revocation, and role changes without a watcher or stale authorization cache. Initial failure prevents authenticated startup; later failure denies protected admissions with safe HTTP 503. A valid replacement restores evaluation. The ceiling is an input bound, not a measured throughput guarantee.

Standalone clients read their selected secret file per request. Trusted library callers and an admitted proxy can supply an explicit in-memory bearer with the same endpoint binding; it is never persisted or obtained from ambient authentication. Policy readers never issue credentials or consult an external identity database.

Alternative considered: signed bearer tokens or OIDC. They add key-discovery, claim, expiry, and revocation contracts that this hub-provisioned allowlist does not need. Revisit when a concrete hub integration requires an established federation contract.

### 3. Classify Operations at the Matched Route

Authenticate at the outer gateway HTTP boundary before diagnostic/plugin lifecycle handlers can expose private failures or parse bodies. Retain only safe principal and grant identity in request context. Host-controlled route admission checks the matched route's required authority before invoking its original handler.

Use the existing route inventory and framework route matching. Core routes require explicit classification, including any documentation routes that remain enabled. Disable automatic documentation endpoints in authenticated mode to keep that surface small. Missing core classifications block authenticated publication. Plugin routes default to operator and cannot grant anonymous access.

| Surface | Peer | Operator |
| --- | --- | --- |
| Safe status, endpoint descriptor, usage | Allowed | Allowed |
| Ordinary message notification | Allowed | Allowed |
| Ordinary mail lifecycle without owner-file inputs | Allowed | Allowed |
| Explicitly ordinary plugin chat/Mail routes | Allowed | Allowed |
| Queued requests and direct prompt controls | Denied | Allowed |
| Raw keys, interruption, session/model selection | Denied | Allowed |
| Reminders, notifier controls, home/refresh, memory, AG-UI | Denied | Allowed |
| Mail post, binding controls, owner-file attachments | Denied | Allowed |
| Plugin connection/credential controls, undeclared plugin routes | Denied | Allowed |

Peer mailbox permission explicitly delegates reading and ordinary mutation of this owner's mailbox. Authenticated principal provenance stays separate from the mail sender and plugin Actor. A path-bearing attachment form is an owner-file capability: reject it for peers with HTTP 403 before opening any path. Operators retain the existing owner-context path form. This change supplies no peer upload or general file-transfer API.

Extend the public plugin SDK with a small host-validated route access declaration carried by existing route metadata. Keep the current router protocol, namespace conflict validation, and supervised lifecycle. Apply the host guard before plugin execution; do not ask plugins to implement authentication. Classify CCCC chat/Mail routes and connection controls explicitly, and update the independent example.

Alternative considered: method/prefix rules or allowing peers to submit ordinary-looking queued requests. Mixed request kinds, raw-key reminders, file attachments, and plugin connection routes demonstrate why explicit operation authority is needed.

### 4. Reuse Immediate Ordinary Delivery

Add `POST /v1/messages` with the existing ordinary-event input shape: bounded `source_event_id`, `text`, and optional metadata. Keep the 64 KiB ordinary envelope limit and existing finite dispatch deadline defaults.

Extract the narrow shared ordinary-dispatch operation from `dispatch_plugin_event()`. It accepts validated source provenance and an active-source check. Plugin contexts retain their lifecycle checks; HTTP messages supply authenticated caller provenance and a current credential-grant check. Do not invent a synthetic plugin instance for HTTP messages or duplicate backend dispatch.

Retain ready-only, pending-input, hook, body-incarnation, and handoff guards. The gateway constructs the literal notification envelope, so native-looking commands remain content. Recheck an HTTP grant during preparation and before the existing handoff gate; observed revocation withdraws pending dispatch authority. This is not an atomic promise that file replacement cancels input already handed off.

Success means confirmed handoff. Busy/unavailable attempts fail immediately; response loss remains uncertain. Retention and retry stay with the sender. Existing queues and scheduling are operator surfaces, with no new queued request kind.

Alternative considered: a command blacklist on existing prompt routes. Native commands vary by backend and can change independently; an ordinary envelope supplies a stable authority boundary.

### 5. Keep Stable Access Selection Separate From Live Addresses

Add typed access selection to supported Python launch/attach inputs and `--access-config PATH` on the maintained scoped gateway attach command. The owner-side document selects mode, listener settings, optional advertised URL, policy file, and owner-client credential reference. It contains references rather than bearer values.

For delegated operations, pass the lexical configuration path through the fixed executor request and validate/open it only in the captured owner context. Extend both closed gateway-attach argument validators. Never accept arbitrary owner argv or resolve the path in the caller before delegation.

Persist the selection in private owner-side gateway settings with a stable reference from runtime authority, so detach and relaunch cannot erase protection. Update strict manifest/gateway models and their producers/readers together as needed. Keep policy references out of registry exports, public status, tmux discovery variables, and harness environments. Live access-selection changes require gateway restart; equivalent attach can reuse an instance. Reject conflicting live selection before persisting candidate settings.

Represent three addresses explicitly in resolved state:

- Bind host/port, preserving current bind-time ephemeral-port resolution.
- Owner-local connect URL, normally derived from the actual bound listener with wildcard translated to owner loopback.
- Explicit advertised remote URL, preserving its HTTPS origin and optional proxy prefix.

Persist desired listener/advertisement settings privately and publish resolved live values only after binding and access validation. Clear live availability on stop while retaining the access selection. Public remote descriptors exclude owner-local paths and all credential references.

Alternative considered: infer the remote URL from Host headers or rewrite owner coordinates on the caller. Neither establishes the externally provisioned proxy route, and foreign loopback has a different meaning on the caller host.

### 6. Bind Clients to Endpoints and Preserve Transport Policy

Extend the existing client with an explicit base-URL mode and a private credential binding. A standalone remote binding includes the expected agent/context and exact origin/base path. Owner-side runtime clients bind to their validated local authority after listener resolution; the hub binds to its separately provisioned remote URL.

Centralize header application for typed and JSON/plugin calls. Preserve base-path prefixes, HTTPS certificate verification, finite timeouts, and existing direct-by-default proxy behavior. Disable redirects rather than trying to follow and selectively strip credentials. Reject URL userinfo, query, fragment, and non-loopback plaintext credential transport. Keep existing native-home ETag checks.

Wire explicit owner credentials into runtime status/control, live-plugin attach reuse, the scoped CLI, and necessary maintained backing clients. Health readiness remains anonymous. Authentication errors are terminal request outcomes; do not retry mutations, downgrade to HTTP, select ambient credentials, or change control transport.

The supported remote recipe terminates TLS at an operator-provisioned reverse proxy, forwards the bearer header, and protects its backend connection. Most deployments keep the gateway on loopback; container deployments expose only the proxy or otherwise isolate the backend. A deliberately configured SSH tunnel uses a loopback client URL. Gateway authentication remains required even if the proxy supplies its own access controls.

Alternative considered: add certificate issuance, native TLS hosting, or automatic URL failover to the gateway. A qualified proxy recipe satisfies the deployment contract without those additional lifecycles.

### 7. Close Selected-Agent Alternate Ingress

Resolve a protected target's access intent from retained owner-side authority, not solely a discovery flag or current gateway record. Add one shared per-target admission path to maintained passive-server handlers. Classify private observation and artifacts as operator operations, alongside direct turn, interrupt, stop, gateway attach/detach, and existing privileged proxies.

Apply the check to direct managed-headless matches as well as registry-resolved agents. Keep global safe identity discovery separate from private state. After detach or stopped-state resolution, retained access intent still governs access. HTTP 401/403 must survive proxy translation, including the bearer challenge; no refusal can trigger tmux, direct headless, registry cleanup, or another transport.

An admitted proxy forwards the caller's explicit bearer only to the resolved validated owner-local gateway. It never substitutes a stored operator secret. The server-managed gateway adapter's existing backing calls instead use its explicitly provisioned owner-service credential. The selected backing handlers validate that credential against the same target policy; no source-address or gateway-header exception is added.

Remote passive-server global launch, discovery, and administration are not qualified by this work. A service with independently available unauthenticated owner-level launch/administration can undermine any per-agent policy. The supported recipe exposes only the secured gateway. If a managed backing server is required, its global administrative surface must already be isolated from ordinary callers by the provisioned deployment. Do not claim that selected-agent guards harden a separately exposed owner-level service.

Alternative considered: leave direct passive controls unchanged or solve all passive-server remote authorization now. The former leaves a bypass; the latter changes the selected remote entry point and expands identity/discovery/global administration scope.

### 8. Revalidate Streams Without Owning Agent Cancellation

Bind authenticated AG-UI streams to credential/grant identity. Reuse existing heartbeat and event-emission points to revalidate; cap the authenticated idle heartbeat at five seconds. Revoke on missing credentials, reduced authority, owner mismatch, or unavailable policy, and close only the affected stream.

Preserve current stream bookkeeping and disconnect semantics. Already admitted work continues independently of stream closure. A new connection must authenticate again. Do not store bearer values in AG-UI registries, event logs, graphics, or browser URLs.

Alternative considered: a credential watcher plus cancellation registry for all active work. Heartbeat revalidation closes the information stream with a documented finite delay without acquiring unrelated runtime cancellation authority.

### 9. Use Existing Evidence and Test the New Boundaries

Extend current gateway/client/plugin/passive/execution suites rather than adding a second harness. Existing plugin tests already establish literal event envelopes, body replacement, dispatch uncertainty, private-source validation, and both gateway process modes.

Add focused evidence for route-classification completeness; 401/403 before effects; mixed requests/reminders/file-input escalation; all three secured listener checks; policy rotation and malformed replacement; credential redaction; endpoint prefix, certificate, redirect and retargeting rules; stream revocation; and direct passive/headless bypass prevention.

Exercise remote offline and online mail with current binding IDs and existing backend fixtures. Verify CCCC ordinary calls and privileged connection denial through its independently installed package. Use a real gateway process behind a fixture-owned TLS proxy for the supported deployment, including separate-user access through the #81 fixtures. Use isolated tmux sockets with inherited selectors cleared. Native-agent checks must use the maintained fixture workflow with explicit case/model and unattended operation.

Classify future files by purpose: product modules under `src/houmao/`, CI under the matching test trees, reusable qualification helpers under `scripts/qualification/gateway-access/`, references under `docs/reference/`, and disposable evidence under an ignored purpose-specific scratch tree. Credential-bearing runs and generated keys remain outside the checkout.

Run required format, lint, strict type checking, unit tests, affected integration suites, and documentation/distribution checks when implementing. Stop broadening checks after required checks and material changed risks are covered. Capacity claims require measurements; functional qualification alone does not establish a production request-rate ceiling.

## Risks / Trade-offs

- [Policy file I/O adds per-admission work] -> Bound file size and use a credential-ID lookup within each validated read. Add caching only if measurements justify a revocation-preserving design.
- [Private attachment paths escape mailbox authority] -> Require operator authority for path-bearing forms before file access; document that peer upload is outside this version.
- [Middleware order exposes plugin errors before authentication] -> Install the authentication boundary outside lifecycle/diagnostic handling and verify failed-instance and malformed-body cases.
- [Protected access disappears after detach or direct headless resolution] -> Retain owner-side intent and test absent live/discovery records explicitly.
- [Backing service or another owner-level service bypasses the gateway] -> Guard maintained target routes and isolate independently privileged global services in the deployment. Same-UID owner processes remain inside the OS trust boundary.
- [Revocation races with already handed-off work] -> Recheck prepared grants, document admission-time effects and the five-second idle-stream bound, and preserve uncertainty instead of claiming rollback.
- [Metadata retargeting discloses a credential] -> Pin origin/base path and expected owner identity, require explicit rebinding, and reject redirects.
- [Updating endpoint schemas breaks tokenless consumers] -> Update maintained clients and strict schema inventories together and return explicit authentication/schema errors without compatibility shims.

## Migration Plan

1. Land current strict access/configuration models, route classifications, private-source validation, and persisted owner protection before enabling broader listeners. Keep trusted-local loopback as the default.
2. Wire owner-local and managed backing clients, executor attach, passive target guards, and registry publication together. Authenticated activation must not precede these boundary checks.
3. Provision the policy and separate client secrets externally. Stop/restart only the gateway to select authenticated mode and its advertised URL; leave the agent body and conversation running.
4. Configure and qualify the HTTPS proxy with protected backend access. Distribute the non-secret endpoint descriptor separately from credentials. Exercise peer/operator mail, plugin, control, rotation, and alternate-ingress checks before marking #84 complete.
5. Rotate by publishing overlapping policy entries, replacing selected client secret contents, and removing old entries. A malformed replacement fails closed until corrected.
6. Roll back by withdrawing remote exposure first, then explicitly restoring a stopped gateway's trusted-local loopback configuration. Never auto-downgrade access or mutate old strict schemas in place. Preserve owner runtime state and provisioned files for deliberate reconciliation.

