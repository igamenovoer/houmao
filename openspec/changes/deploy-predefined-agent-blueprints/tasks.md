## 1. Authoring Workspace Contracts

- [ ] 1.1 Add typed paths and models for `intent/src`, minimal `intent/derived`, and `agent-definition`
- [ ] 1.2 Implement `init-intent` so it creates only `agent-def-overview.md`
- [ ] 1.3 Resolve only overview-referenced supporting files with confinement and file-kind checks
- [ ] 1.4 Compute source-set and derived-material digests and stale-state diagnostics
- [ ] 1.5 Add focused unit tests for source ownership, reference confinement, and freshness

## 2. Derivation, Approval, and Materialization

- [ ] 2.1 Implement `interpretation.md` and normalized `materialization.toml` generation
- [ ] 2.2 Validate and copy source Agent Skill directories into derived materials
- [ ] 2.3 Implement `validation.json` and digest-bound `approval.toml`
- [ ] 2.4 Implement preview and write modes for immutable Agent Definition Revisions
- [ ] 2.5 Reject stale approval, unsafe files, reserved skill names, and source-path dependencies
- [ ] 2.6 Add materialization provenance and focused authoring lifecycle tests

## 3. Agent Definition Revision Schemas

- [ ] 3.1 Add versioned models for `definition.toml`, `deploy-contract.toml`, and `instance-contract.toml`
- [ ] 3.2 Add typed deployment inputs, structured bindings, exact text markers, and context-safe rendering
- [ ] 3.3 Reject unknown markers, executable expressions, unused inputs, and undeclared content edits
- [ ] 3.4 Add whole-revision identity and digest validation
- [ ] 3.5 Package and validate one built-in reference Agent Definition Revision

## 4. Deployment Request and Plan

- [ ] 4.1 Add Deployment Request models and non-secret serialization
- [ ] 4.2 Add deterministic binding resolution and final component validation
- [ ] 4.3 Add Deployment Plan staging beneath the selected project overlay
- [ ] 4.4 Record definition, request, rendered-file, project-precondition, and plan digests
- [ ] 4.5 Reject stale requests, project collisions, unresolved markers, and edited plans
- [ ] 4.6 Add plan preview and focused request-to-plan tests

## 5. Project Apply and Catalog Ownership

- [ ] 5.1 Add Agent Deployment catalog tables, relationships, and explicit project migration
- [ ] 5.2 Add managed deployment content paths and immutable registered-skill cache reuse by digest
- [ ] 5.3 Implement journaled apply states and operation-owned filesystem staging
- [ ] 5.4 Make the Agent Deployment catalog-visible only after every staged artifact is ready
- [ ] 5.5 Implement doctor recovery for interrupted precommit and postcommit publication
- [ ] 5.6 Implement ownership-aware inspect, doctor, update, and removal
- [ ] 5.7 Block instance-contract updates and removal while live or preserved instances reference the deployment
- [ ] 5.8 Add failure-injection, drift, migration, and lifecycle tests

## 6. CLI and System Skills

- [ ] 6.1 Add maintained definition init, derive, approve, materialize, validate, plan, apply, inspect, doctor, update, and remove commands
- [ ] 6.2 Fold authoring and deployment guidance into the existing `houmao-agent-definition` subskill
- [ ] 6.3 Remove the proposed competing `houmao-agent-definition-authoring` route
- [ ] 6.4 Update admin-entrypoint, shared-routines metadata, generated prompts, and actor restrictions
- [ ] 6.5 Return the maintained profile launch command without running it

## 7. Use Cases, Documentation, and Verification

- [ ] 7.1 Update behavior-testing cases for manual and implicit UC-01 and UC-02 routing
- [ ] 7.2 Document source, derived, revision, request, plan, deployment, and separate launch terminology
- [ ] 7.3 Remove stale blueprint, semantic-adaptation, and physical-atomicity language
- [ ] 7.4 Run focused suites plus `pixi run format`, `pixi run lint`, `pixi run typecheck`, and `pixi run test`
- [ ] 7.5 Build and check distributions and run strict OpenSpec validation
