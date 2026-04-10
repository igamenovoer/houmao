## 1. Split The Fixture Roots

- [x] 1.1 Create `tests/fixtures/plain-agent-def/` with the maintained direct-dir layout, including `launch-profiles/`, tool auth roots, and the tracked role/preset/skill/setup assets that belong to the plain filesystem lane.
- [x] 1.2 Create `tests/fixtures/auth-bundles/` for local-only credential bundles and move the maintained bundle names, README guidance, and encrypted archive/checksum workflow into that root.
- [x] 1.3 Retire `tests/fixtures/agents/` from the maintained contract by removing maintained contents from that path or replacing it with a narrow redirect note.

## 2. Update Maintained Demos And Smoke Flows

- [x] 2.1 Update the shared TUI tracking demo pack code, tests, and README/config guidance to source host-local auth from `tests/fixtures/auth-bundles/` while continuing to build from demo-local `inputs/agents/`.
- [x] 2.2 Update the minimal agent launch demo code, tutorial, and tests to source host-local auth from `tests/fixtures/auth-bundles/`.
- [x] 2.3 Update the Claude `official-login` smoke flow and its documentation to build from a temporary direct-dir copy of `tests/fixtures/plain-agent-def/` and to materialize `official-login` there from `tests/fixtures/auth-bundles/claude/official-login/`.

## 3. Update Narrow Runtime Fixtures And Guidance

- [x] 3.1 Update narrow runtime, mailbox, and probe-skill tests/helpers to reference `tests/fixtures/plain-agent-def/` instead of the overloaded `tests/fixtures/agents/` root.
- [x] 3.2 Update maintained fixture guidance and maintained docs/manual references so they describe the split fixture lanes and stop calling one repository tree canonical for every workflow.
- [x] 3.3 Leave archival `scripts/demo/legacy/` references explicitly legacy rather than migrating them into the maintained fixture contract.

## 4. Verify The Split Contract

- [x] 4.1 Run focused unit and integration coverage for direct-dir credential flows, shared TUI demo asset loaders, minimal demo asset loaders, and any updated path-resolution helpers.
- [x] 4.2 Run the maintained Claude `official-login` smoke validation flow against the new temporary direct-dir materialization contract when local credentials are available.
