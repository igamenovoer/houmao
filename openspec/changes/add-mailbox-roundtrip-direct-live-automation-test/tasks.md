## 1. Isolated Live Demo Execution

- [x] 1.1 Add test-owned runtime setup for the mailbox tutorial pack that uses a fresh demo output directory, a picked free loopback `CAO_BASE_URL`, and an isolated `AGENTSYS_GLOBAL_REGISTRY_DIR`.
- [x] 1.2 Update the tutorial-pack live automation path so `start` and `roundtrip` use the direct live-agent mail path without depending on `attach-gateway`, `gateway-send-prompt`, or fake mailbox injection.
- [x] 1.3 Ensure the live automation can stop and restart its owned CAO instance safely and surfaces ambient ownership or shared-registry conflicts as explicit failures.

## 2. Live Integration Coverage

- [x] 2.1 Add a dedicated live automatic workflow target for `scripts/demo/mailbox-roundtrip-tutorial-pack` that runs `start`, `roundtrip`, `verify`, and `stop` against a fresh temp-root demo output directory; this may be a live integration test, a scripted runner, or another owned multi-step automation sequence.
- [x] 2.2 Keep the existing fake-harness scenario-runner coverage as a separate fast regression layer rather than using it to satisfy the new live requirement.
- [x] 2.3 Add assertions that the live automation target starts two real agents and fails if the direct mail path returns sentinel parsing, prompt execution, or other live runtime errors.

## 3. Mailbox Artifact Assertions

- [x] 3.1 Add helpers and test assertions that inspect `<demo-output-dir>/shared-mailbox/mailboxes/<sender-address>/` and `<demo-output-dir>/shared-mailbox/mailboxes/<receiver-address>/` after a successful run.
- [x] 3.2 Assert that canonical send and reply Markdown message documents exist under `<demo-output-dir>/shared-mailbox/messages/`, can be opened and read, and match the tracked initial and reply input Markdown files.
- [x] 3.3 Assert that inbox and sent projections for both agents resolve to the canonical send and reply messages and preserve expected thread linkage after `stop`.

## 4. Verification And Documentation

- [x] 4.1 Preserve the sanitized verification contract while ensuring the live test proves that raw readable mailbox content remains on disk for manual inspection.
- [x] 4.2 Run the new live automatic workflow target plus the existing targeted mailbox tutorial-pack tests and confirm the live path passes using owned isolated state.
- [x] 4.3 Update tutorial-pack maintainer documentation to clarify that automatic live coverage uses fresh isolated state and leaves inspectable mailbox artifacts under the completed demo output directory.
