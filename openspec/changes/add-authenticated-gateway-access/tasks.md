# Tasks

## 1. Private Access Policy and Retained Owner Protection

- [ ] 1.1 Add strict access-selection, owner-bound verification-policy, principal/grant, and explicit client-binding models under supported product code; verify valid peer/operator policies and rejection of unknown roles, duplicate keys/IDs, malformed verifiers, and mismatched agent/context identities through boundary-level unit tests.
- [ ] 1.2 Implement bounded descriptor-based private-file loading and constant-time credential verification with live atomic policy replacement; verify unsafe paths/owners/permissions, absent selected sources, rotation overlap, revoked credentials, role reduction, malformed replacement, recovery, and absence of ambient fallback in focused access tests.
- [ ] 1.3 Persist private access selection through stable owner runtime authority and update affected strict manifest/gateway schema producers and readers together; verify detach, stopped-state lookup, and relaunch retain protection without exporting credential references or accepting incompatible persisted state.
- [ ] 1.4 Document policy/client binding formats, external provisioning, the 1 MiB bound, rotation, and same-UID limits in the gateway access reference; verify examples match the strict models and contain only placeholder secret material.

## 2. Gateway Authentication and Operation Admission

- [ ] 2.1 Add outer HTTP authentication before body parsing and plugin lifecycle handling, with minimal anonymous health and safe 401/403/503 outcomes; verify unauthenticated malformed bodies and failed-plugin probes cause no handler or backend effects.
- [ ] 2.2 Classify every core/AG-UI route using the fixed peer/operator matrix and disable unclassified automatic documentation routes in authenticated mode; verify route-inventory completeness and denial of queued prompt/interrupt, raw keys, session/model selection, reminders, memory, notifier controls, and native refresh for peers.
- [ ] 2.3 Replace mailbox, plugin-activation, and ordinary-event loopback restrictions with the shared deployment policy; verify safe local defaults, authenticated loopback enforcement, rejection of unauthenticated broader binds before publication/imports, and authorized broader-listener availability.
- [ ] 2.4 Update gateway HTTP/status and diagnostic references for access classifications, challenges, and redaction; verify recognizable credentials, verifiers, private paths, headers, and malformed policy values do not appear in public outputs or enabled diagnostics.

## 3. Ordinary Messages and Remote Mailbox Operations

- [ ] 3.1 Extract the shared ordinary-dispatch operation from existing plugin delivery without adding a queue or synthetic plugin identity; verify existing plugin admission, confirmed handoff, body-incarnation, hook, and failure regressions still pass.
- [ ] 3.2 Add strict bounded POST /v1/messages input/results and authenticated source provenance; verify literal native-looking text, rejection of privileged fields, busy refusal, revocation observed before handoff, oversized input, response-loss uncertainty, and absence of replay after recovery.
- [ ] 3.3 Enforce operator authority for mail post/binding controls and every owner-local attachment-path form before file/provider access; verify peers can use ordinary offline/online mail with expected binding IDs, while stale references and unauthorized owner-file reads fail without side effects.
- [ ] 3.4 Document ordinary-message requests, sender-owned retry, remote channel-selected mail, and the owner-path attachment limitation; verify documented examples against the route models and focused gateway mailbox workflows.

## 4. Endpoint Publication, Clients, and Owner-Side Configuration

- [ ] 4.1 Extend shared gateway clients with explicit base URLs, endpoint-bound file or explicit in-memory credentials, common header application, verified HTTPS, and redirect refusal; verify typed and JSON/plugin calls, proxy-prefix preservation, retargeting rejection, certificate failure, per-request secret rotation, no mutation replay, and existing proxy-env behavior.
- [ ] 4.2 Add separate resolved bind/local-connect/advertised fields and secret-free remote descriptor projections to gateway state and registry schemas; verify bind-time ephemeral ports, owner-qualified wildcard handling, explicit advertisement, no Host-header inference, clearing live availability, and exclusion of owner paths and credential references from exports.
- [ ] 4.3 Wire explicit owner client bindings into runtime control, status, live-plugin attach reuse, and scoped manager calls; verify protected local operations succeed with their selected binding, anonymous health readiness still works, and missing credentials never trigger direct or ambient fallback.
- [ ] 4.4 Add typed Python launch/attach access inputs and maintained scoped gateway attach --access-config; extend both closed executor gateway-attach validators and owner dispatch so configuration paths are opened only in the saved owner context; verify target-only paths, rejected unsupported arguments, preserved execution identity, equivalent reuse, and restart-required conflicts without partial persistence.
- [ ] 4.5 Update gateway lifecycle/CLI, registry layout, and execution-context references with the new configuration and descriptor contracts; verify supported command help and examples use houmao-mgr and clearly separate owner-local coordinates from remote endpoints.

## 5. Plugin and CCCC Access Declarations

- [ ] 5.1 Publish the small SDK route-access declaration and enforce it during existing route staging; verify peer/operator declarations, operator defaults, invalid-declaration instance failure before activation, namespace conflicts, and authentication before plugin lifecycle errors.
- [ ] 5.2 Classify maintained CCCC chat and deferred-Mail routes as ordinary where appropriate and connection/credential controls as operator operations; verify peer send/read/reply behavior and privileged denial through the independent package's existing provider fixtures.
- [ ] 5.3 Preserve authenticated broader-listener plugin activation and background ordinary dispatch without passing caller credentials into plugin contexts; verify lifecycle cleanup, current-body guards, credential-source separation, and core availability during plugin failure in both gateway execution modes.
- [ ] 5.4 Update the plugin author guide and independent example with explicit access declarations and remote deployment assumptions; verify the external package still imports only the supported SDK and its installed-wheel route classifications work.

## 6. Passive Target Guards and Managed Backing Calls

- [ ] 6.1 Add shared protected-target admission to maintained passive selected-agent routes, including direct managed-headless matches, private state/history/artifacts, turn submission, interrupt, stop, and gateway lifecycle controls; verify missing live registry/gateway records and detachment do not restore anonymous access or reach tmux/headless/cleanup effects.
- [ ] 6.2 Preserve 401/403 and bearer challenges across gateway proxies, forwarding only an explicitly admitted caller bearer to the validated owner-local endpoint; verify no stored operator substitution, credential persistence, role upgrade, mutation retry, or direct-control fallback after rejection.
- [ ] 6.3 Wire explicitly provisioned owner-service credentials through maintained pair/passive backing clients used by server-managed gateway adapters; verify legitimate inspection/dispatch and operator operations pass target admission while source-address and gateway-header impersonation fail.
- [ ] 6.4 Document protected-target passive compatibility and the requirement to isolate independently privileged global services; verify the supported recipe exposes only secured gateway access and makes no remote passive-server launch/discovery/admin claim.

## 7. AG-UI Stream Admission and Revocation

- [ ] 7.1 Require operator grants for all AG-UI capabilities, connect, runs, events, detach, and destination-state routes; verify anonymous/peer denial before stream or run effects and preserve existing sanitized connect behavior.
- [ ] 7.2 Revalidate admitted stream grants at emission/heartbeat boundaries with a maximum five-second authenticated idle interval; verify revoked credentials, role reduction, and unavailable policy close streams and release bookkeeping without interrupting or replaying agent work.
- [ ] 7.3 Update AG-UI transport documentation with explicit bearer-header usage, reconnect authentication, and the revocation bound; verify examples contain no tokens in stream URLs, event payloads, browser links, or diagnostic records.

## 8. Deployment and Cross-Surface Qualification

- [ ] 8.1 Add a reproducible HTTPS reverse-proxy reference deployment and process-level integration fixture with generated credentials/certificates outside the checkout; verify real TLS verification, path-prefix forwarding, anonymous/peer/operator outcomes, protected backend access, and live rotation without body restart.
- [ ] 8.2 Exercise separate-user owner-local and remote gateway access using the existing execution fixtures and explicitly isolated tmux selectors; verify owner identity, forbidden cross-target credentials, owner-only configuration paths, and an explicitly selected unattended managed-agent fixture without ambient authentication.
- [ ] 8.3 Qualify remote offline/online mailbox workflows and independently installed CCCC ordinary/control routes using their existing service/process fixtures in foreground and detached gateway modes; record actual-service evidence and distinguish unconfigured host/container lanes from passed tests.
- [ ] 8.4 Publish the #84 acceptance map linking requirements/scenarios to the completed tests, deployment recipe, qualification evidence, and real limits; update ROADMAP.md completion only after required evidence is satisfied or the user explicitly accepts a documented deferral.
- [ ] 8.5 Run pixi run format, pixi run lint, pixi run typecheck, pixi run test, affected integration/installed-wheel checks, pixi run docs-build, pixi run build-dist, pixi run check-dist, and strict OpenSpec validation; verify required checks pass and review the final scoped diff for secret material and unrelated changes.

