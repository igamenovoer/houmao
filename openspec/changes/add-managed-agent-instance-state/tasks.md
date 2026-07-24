## 1. Verified-Self Runtime Authority

- [ ] 1.1 Add confined runtime-manifest identity parsing for self operations
- [ ] 1.2 Verify opaque agent id, project, runtime binding, live state, and registry generation
- [ ] 1.3 Cross-check tmux bindings when present without requiring tmux for supported headless runtimes
- [ ] 1.4 Reject copied pointers, stale generations, ambiguous identities, and unmanaged callers
- [ ] 1.5 Add tmux, headless, stale-manifest, and adversarial identity tests

## 2. Canonical Instance-State Store

- [ ] 2.1 Add `.houmao/memory/agents/<agent-id>/state.sqlite` paths and versioned schema
- [ ] 2.2 Add store identity, deployment, instance-contract digest, and launch-attempt metadata
- [ ] 2.3 Add explicit state database migration and integrity checks
- [ ] 2.4 Integrate journaled `preparing`, `prepared`, `starting`, `active`, and `failed` launch states
- [ ] 2.5 Revalidate and reuse compatible preserved-instance state
- [ ] 2.6 Add failure-injection and preserved-instance lifecycle tests

## 3. Runtime Variables

- [ ] 3.1 Extend instance-contract models with typed runtime-variable declarations and consumers
- [ ] 3.2 Add launch value collection, defaults, validation, and revision-one initialization
- [ ] 3.3 Render prompt and memo consumers from one launch snapshot
- [ ] 3.4 Add verified-self list, get, and explain commands
- [ ] 3.5 Add explicit-target admin compare-and-set mutation and revision history
- [ ] 3.6 Reject secret-bearing declarations and mutations
- [ ] 3.7 Add isolation, relaunch, snapshot, mutation, and no-implicit-prompt tests

## 4. Named Mindsets

- [ ] 4.1 Extend instance-contract models with mindset declarations, stable question ids, bounds, and skill bindings
- [ ] 4.2 Initialize every declared mindset at fresh launch and preserve compatible revisions on relaunch
- [ ] 4.3 Add one-transaction immutable snapshots for all mindsets required by one skill
- [ ] 4.4 Add explicit-target admin inspection and optimistic revision mutation
- [ ] 4.5 Validate low-authority content and reject tool, gate, instruction, credential, or evidence authority
- [ ] 4.6 Validate bound static-skill snapshot instructions without claiming runtime interception
- [ ] 4.7 Add manual and implicit skill behavior cases for successful and fail-closed mindset lookup

## 5. Deployment, Routing, and Verification

- [ ] 5.1 Preserve exact instance-contract declarations and digest through deployment
- [ ] 5.2 Block incompatible deployment updates while live or preserved instances reference the old digest
- [ ] 5.3 Update admin, agent, shared-routines, and agent-instance skill routing
- [ ] 5.4 Update generated prompts and runtime-state documentation
- [ ] 5.5 Run focused suites plus project format, lint, typecheck, and unit tests
- [ ] 5.6 Build and check distributions and run strict OpenSpec validation
