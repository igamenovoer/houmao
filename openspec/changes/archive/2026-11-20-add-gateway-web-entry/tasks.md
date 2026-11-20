# Tasks

## 1. Verified Native Destinations

- [x] 1.1 Add an owner-private browser entry description and a URL builder for backend-selected path, query, and fragment values. Test same-origin construction, component encoding, safe error text, and rejection of any destination that changes the verified authority.
- [x] 1.2 Expose the DSH root browser exchange from the read-only owned Web adapter. Test private bootstrap checks, listener and companion identity checks, rejection of a replaced host, and preservation of the API peer. Document the native cookie and sidebar selection in the DSH Web reference.
- [x] 1.3 Expose the Kimi fragment destination through its verified browser credential path. Qualify the native session link on 2.6.0 and use the verified root with native selection if needed. Test stale host refusal and private fragment construction, and record the qualified path in the Kimi Web reference.

## 2. Gateway Ticket Issuance and Redemption

- [x] 2.1 Add direct signed issuance with proof-required route admission and an enrolled-admin role check before native access. Test HTTP 401 without valid proof on an empty roster, HTTP 403 with self or delegated proof, and successful enrolled-admin issuance. Verify other authenticated and public gateway actions retain their existing route classifications.
- [x] 2.2 Add the bounded per-listener ticket store, monotonic 60-second expiry, and atomic single consumption. Test expiry during revalidation, concurrent redemption, wrong gateway, listener restart, and stale admin enrollment using deterministic clocks and identity fixtures.
- [x] 2.3 Wire redemption to the current owner and the full native Web execution identity. Test success while native input is busy, refusal for stopped or unsupported targets, and stale binding refusal after an exact relaunch or listener replacement with reused native identifiers. Verify refusal triggers no lifecycle or prompt operation.
- [x] 2.4 Enforce the owner-local origin and peer for issuance and redemption, and add no-store, no-referrer, and fixed error handling. Test advertised HTTP proxy and passive relay refusal, rejection of duplicate or extraneous query parameters and caller destinations, and exclusion of credentials from diagnostic logs, events, validation errors, and public state. Document route semantics in the gateway protocol reference.

## 3. Interactive Login

- [x] 3.1 Add explicit same-origin login start and the bounded pending attempt store. Verify the purpose-specific challenge binds the issuer, approval route, live execution, and expiry. Test expiry, capacity, restart, and isolation of the browser claim secret from the signing challenge and command.
- [x] 3.2 Add the owner-local terminal proof callback using the current admin roster and bounded SSHSIG verification. Test stock OpenSSH signatures, an unenrolled candidate before a valid enrolled signer, proof size limits, replay, wrong purpose and target, and failure with self or delegated proof. Verify the callback reports only an outcome and logs no proof.
- [x] 3.3 Serve the minimal login page at the bare entry URL and generate the copyable local command. Test safe quoting of literal key paths, blank-path SSH agent selection, safe no-key output, and direct curl submission without copying a signature back. Verify a valid ticket bypasses the page and malformed or expired tickets show fresh-login guidance.
- [x] 3.4 Add browser polling and one-time claim through the existing ticket issuer. Test wrong-tab refusal, concurrent claims, expired or revoked approval, and native replacement before claim. Verify automatic navigation with the normal ticket and absence of login secrets in diagnostics and shared browser storage. Document the login route contracts.

## 4. Operator Commands and Documentation

- [x] 4.1 Add the signed gateway client method and scoped `gateway web-entry` manager command. Test explicit enrolled signer selection, ticket-only plain and JSON output, gateway detachment, wrong mode, signer refusal, and unsupported remote selection. Verify failure performs no unsigned retry and the signed client never follows the browser redirect.
- [x] 4.2 Document the bare URL and signed CLI flows, local key selection, terminal prerequisites, private-link handling, fresh-login recovery, provider session selection, and exact dual-loopback forwarding. Include a Mermaid sequence diagram and verify the examples against the page, callback, and CLI tests.

## 5. Integrated Qualification

- [x] 5.1 Run fresh Playwright browsers through the signed DSH ticket and the interactive terminal flow using an explicit key path on DSH 0.2.2-rc.3. Verify native cookie creation, a clean URL, selection of the managed conversation, and coexistence with the programmatic peer. Verify automatic continuation and that browser entry reads no fixture bootstrap or native connection file.
- [x] 5.2 Run the Kimi 2.6.0 browser flow through the same gateway using an isolated SSH agent with both unenrolled and enrolled keys. Verify blank-path signing, automatic continuation, and native fragment authentication for the bound conversation. Verify exact-address private forwarding and continued operation of the advertised HTTPS gateway's signed API.
- [x] 5.3 Run the affected gateway, manager, and Web integration suites with isolated tmux and fixture roots. Run `pixi run lint`, `pixi run typecheck`, `pixi run test`, `pixi run docs-build`, and `openspec validate add-gateway-web-entry --strict`. Record tested native versions, results, and any known blockers in the change's `logs/` without credential material.
