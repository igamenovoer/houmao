# Tasks

## 1. Owner State and Admin Enrollment

- [ ] 1.1 Add strict launch seed, retained key list, current self, and client binding models. Verify zero and multiple initial keys, malformed OpenSSH keys, duplicate keys and fields, and mismatched owner bindings.
- [ ] 1.2 Persist owner-bound admin state and its revision through bounded private storage. Verify first launch with an empty list, startup with preloaded keys, restart, stopped-state lookup, and relaunch with live membership retained. Verify missing or corrupt initialized state fails closed.
- [ ] 1.3 Provision a distinct Ed25519 self key pair per launch or join generation. Check private-key storage and current owner binding in tmux and headless paths. Test same-generation gateway restart, stale or foreign keys, and secret-free runtime exports.
- [ ] 1.4 Declare `cryptography` as a runtime dependency and add in-process SSHSIG signing and verification with bounded framing. Check stock `ssh-keygen -Y sign` interoperability and rejection of malformed envelopes, wrong namespaces or keys, and unsupported algorithms. Verify admission with SSH executables absent.
- [ ] 1.5 Issue bounded single-use challenges for self, admin, and first registration. Test wrong purpose, revision, generation, target, origin, method, path, query, or body digest, and expiry and replay. Verify admission before body parsing or effects.
- [ ] 1.6 Add post-start first-key registration and live admin addition and removal. Verify proof of the proposed first key, atomic competing registrations, multiple admins, stale grants at mutation commit, key revocation, and reopening after final removal.
- [ ] 1.7 Document manifest seeding, self key lifetime, signer selection, enrollment, and final removal. Verify safe examples and explain same-UID authority and reachability for an empty list.

## 2. Route Admission and Listener Policy

- [ ] 2.1 Apply route admission before protected body parsing, plugin lifecycle handling, or effects. Verify applicable HTTP 401 challenges, 403 for insufficient proof, safe policy-unavailable 503, and minimal public health.
- [ ] 2.2 Classify core and AG-UI routes and block unclassified publication. Test private status, usage, and memory with current self and verified admin proof, and admin controls in both valid empty and key-required states.
- [ ] 2.3 Replace mailbox, plugin-activation, and ordinary-event loopback checks with the shared deployment policy. Verify explicit validated broader binds, protected loopback admission, and startup refusal before publication or plugin imports when required state is invalid.
- [ ] 2.4 Update API and diagnostic references for route classes, challenge errors, and caller provenance. Check responses and logs for signatures, replayable challenges, secrets, roster details, raw headers, private paths, and privileged content.

## 3. Public Input and Private Mailbox

- [ ] 3.1 Extract shared immediate dispatch from plugin delivery and verify existing plugin lifecycle, current-body, readiness, hook, and confirmed-handoff behavior.
- [ ] 3.2 Implement bounded `POST /v1/messages` and `POST /v1/public/prompt` with gateway-authored public provenance. Test anonymous and signed callers, native-looking text, forged labels, control fields, size bounds, and preservation of pending admin overrides.
- [ ] 3.3 Enforce public-input enablement, finite admission, and one-way outcomes independently of admin list state. Verify disabled and rate-limited calls, busy refusal, body replacement, uncertain handoff, and handoff-only responses when a separate reply is requested.
- [ ] 3.4 Require private proof for routine mail. Apply live admin access to post and binding controls and require verified admin proof for owner-file forms on private routes. Test both mail channels and stale bindings. Verify denial before provider or filesystem effects.
- [ ] 3.5 Wire routine mailbox skills through managed self signing or an explicit admin signer. Verify the normal CLI handles challenges and channel selection, resolver and command output omit proof material, and admission failures end the call. Exercise the separately authorized gateway-absent path independently.
- [ ] 3.6 Document and exercise public input examples and handoff and retry semantics, separate reply channels, private mailbox operations, and owner-file attachment handling.

## 4. Endpoint Publication and Client Proof

- [ ] 4.1 Extend shared clients with exact target and URL binding, self and admin signing, verified HTTPS with deployment trust, and redirect refusal. Test typed and plugin calls, challenge validation before signing, prefix and proxy behavior, retargeting, and certificate failure.
- [ ] 4.2 Publish distinct bind, owner-local, and advertised endpoints plus a minimal descriptor. Verify ephemeral ports, owner wildcard handling, open and key-required publication, stale discovery after registration, clearing on detach, and secret-free exports.
- [ ] 4.3 Wire automatic signing through `houmao-mgr agents self ...` and explicit admin signing into runtime status, control, and live-plugin reuse. Verify current self key selection, unsigned public readiness, and terminal failure when challenge or proof checks fail.
- [ ] 4.4 Add launch manifest admin seed inputs and scoped gateway attach `--access-config` for deployment settings. Verify finite executor validators, owner-side path resolution, equivalent reuse, and restart-required conflicts without resetting live membership.
- [ ] 4.5 Update scoped CLI help, registry layout, execution references, and deployment examples. Verify distinct addresses, verified deployment trust, and the challenge and enrollment examples.

## 5. Plugins and CCCC Access

- [ ] 5.1 Publish SDK route declarations and enforce them during staging. Verify private and admin classification, admin defaults in both key states, invalid public declarations, namespace checks, and admission before private plugin errors.
- [ ] 5.2 Classify CCCC routine chat and deferred Mail as private and connection and credential controls as admin. Verify self and verified admin ordinary access and the empty or key-required control rule using independent provider fixtures.
- [ ] 5.3 Preserve broader-listener activation and background dispatch with configured service authority. Verify worker cleanup, current-body guards, separation of caller and provider proof, and core availability during plugin failure.
- [ ] 5.4 Update the plugin guide and independent example and verify installed-wheel imports, route classification, and behavior under both admin states.

## 6. Passive Target Guards and Backing Authority

- [ ] 6.1 Apply retained policy to direct headless matches, private reads, raw artifacts, turns, interrupt, stop, and gateway lifecycle. Verify both admin states through detach and absent discovery, missing policy refusal, and existing admitted 501 outcomes.
- [ ] 6.2 Verify self and admin signatures at passive ingress and relay only the admitted caller's scope. Test path and body translations, one-use relay, stale self generation, admin revocation and first-enrollment races, and challenge and status translation without credential substitution.
- [ ] 6.3 Provision separate owner-service bindings for necessary maintained backing operations. Verify current target binding, continued backing through first enrollment, and denial of caller-supplied source claims or service proof on unrelated operations.
- [ ] 6.4 Document retained passive access, proxy challenges, the backing boundary, and admitted lifecycle outcomes. Verify remote deployment exposes the per-agent gateway and isolates global passive administration.

## 7. Admin AG-UI Streams

- [ ] 7.1 Apply both admin access states to AG-UI capabilities, connect, runs, events, detach, and destination state. Verify anonymous open admission, signed admission, and refusal when listed-key proof is required.
- [ ] 7.2 Revalidate on events and at most every five seconds while idle. Verify first enrollment closes open streams, key removal and re-enrollment close affected verified streams, and target or policy failure closes both. Check bookkeeping and continued handed-off work.
- [ ] 7.3 Update AG-UI transport examples for header-carried proof, open admission, and reconnect. Verify challenge and proof material stay out of browser URLs, events, and diagnostics.

## 8. Deployment and Cross-Surface Qualification

- [ ] 8.1 Qualify a real HTTPS reverse proxy with generated keys and certificates outside the checkout. Exercise zero-key startup, post-start enrollment, multiple admins, final removal, one-way public input, signed self CLI access, protected backend traffic, and path prefixes.
- [ ] 8.2 Exercise separate-user access using existing execution fixtures and isolated tmux selectors. Verify owner-only launch inputs, distinct signers and targets, stale self keys, and an explicitly selected unattended agent fixture.
- [ ] 8.3 Qualify remote offline and online mail and installed CCCC ordinary and control routes in foreground and detached modes. Record actual-service evidence and identify deferred or unconfigured host and container lanes.
- [ ] 8.4 Publish the #84 acceptance map linking public input, private proof, open admin access, key enrollment and revocation, and verified transport to evidence. Update the roadmap after required checks pass or a deferral is accepted.
- [ ] 8.5 Run the required Pixi format, lint, typecheck, unit, affected integration, docs, distribution, and installed-wheel checks. Run strict OpenSpec validation and inspect the scoped diff for unrelated changes and credential material.

