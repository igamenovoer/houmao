## 1. Demo-pack scaffold and dual-authority lifecycle

- [x] 1.1 Scaffold `scripts/demo/passive-server-parallel-validation-demo-pack/` with the required README, stepwise and autotest wrappers, case guides, helper code, and pack-owned inputs/agent selectors.
- [x] 1.2 Implement preflight plus dual-authority startup/shutdown helpers that create one shared runtime/registry root, separate old/passive authority roots, configurable ports, and health verification for both servers.
- [x] 1.3 Persist run metadata and evidence directory structure so stepwise commands can reuse the same authority URLs, roots, and launched agent identities across phases.

## 2. Shared interactive parity and gateway validation

- [x] 2.1 Implement shared interactive agent provisioning through the local managed-agent launch path and capture both authorities' list/resolve outputs for the same agent.
- [x] 2.2 Implement managed summary/detail/history comparison helpers that normalize authority-specific fields, emit parity results, and preserve raw HTTP snapshots for the `inspect` and `auto` phases.
- [x] 2.3 Implement the gateway phase so the passive server submits a prompt through its gateway proxy surface and the workflow verifies follow-up state/history evidence from both authorities.

## 3. Headless visibility and stop-propagation validation

- [x] 3.1 Implement the headless phase that launches a headless agent through `POST /houmao/agents/headless/launches` on the passive server and verifies old-server discovery or resolve visibility for that same agent.
- [x] 3.2 Implement the stop phase that stops a shared validation agent through the passive server and verifies disappearance from both authorities plus shared runtime liveness evidence.
- [x] 3.3 Wire the unattended autotest cases (`parallel-preflight`, `parallel-all-phases-auto`) to cover the shared interactive, gateway, headless, and stop-propagation phases.

## 4. Reporting, docs, and verification

- [x] 4.1 Implement report generation, sanitization, expected-report comparison, and snapshot-refresh support for the dual-authority evidence schema.
- [x] 4.2 Write operator-facing README guidance and interactive case docs for running the stepwise and unattended Step 7 workflows on separate old/passive server ports.
- [x] 4.3 Run the relevant lint, test, and demo validation commands for the new pack, capture a baseline sanitized report, and update tracked expected output as needed.
