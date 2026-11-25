# Tasks

## 1. Receipt Lookup

- [x] 1.1 Extend the authorized gateway delivery route to resolve exactly one `handle` or `event_ref` through its existing scope checks. In `test_cccc_plugin.py`, verify incoming, outgoing, and history handles select the same event and receipt projection as a reference. Cover malformed and duplicate selectors, expired and foreign handles, generation changes, and authorization denial. Verify rejected requests issue no provider receipt lookup.
- [x] 1.2 Add the gateway `chat deliveries --handle` target and reuse instance inference. In `test_cccc_client.py`, cover gateway handle and event-reference targets, direct native IDs, every wrong-mode form, explicit instance mismatch, and safe stale-handle and invalid-reference guidance. Update the gateway guide with sender and recipient examples and exact-history recovery.

## 2. Membership Discovery

- [x] 2.1 Implement `members --group` in both modes and check the assertion in the authorized gateway route or against the verified direct Actor binding. Test matching, omitted, mismatched, malformed, and repeated assertions. Verify the same public projection on success and no provider membership request on conflict. Explain implicit Group selection in the package and gateway guides.

## 3. CLI Help and Usage Diagnostics

- [x] 3.1 Add installed-metadata `--version` and exact gateway and direct command examples in top-level help. Document receipt targets and the Group assertion in subcommand help. Test the examples against the parser and verify help and version never resolve a profile, signer, or service connection.
- [x] 3.2 Make unsupported flags and targeted usage failures actionable using fixed diagnostic templates and safe option identifiers. Test separate and attached sensitive values, inappropriate target flags in both modes, and malformed arguments. Verify private input stays out of diagnostics and existing authorization and uncertain-mutation handling still pass.

## 4. Integrated Qualification

- [x] 4.1 Build and install the optional wheel in the installed-distribution qualification environment. Verify `--version` matches its wheel metadata. Against compatible receiver-v2 CCCC, compare handle and reference receipt results, exercise direct native-ID lookup and Group assertion, and confirm newest-first results and `has_more` on a limited receipt history.
- [x] 4.2 Run `agent-cccc/two-agent-chat-round-trip` against two managed coding agents and the installed CLI. Capture sender inspection by the send-result `event.handle` and recipient inspection by the incoming fence handle. Compare the reported event and attempt with the independent provider view and verify exact reply ancestry and the compact fence. Keep the new caller-side invocations in the case evidence.
