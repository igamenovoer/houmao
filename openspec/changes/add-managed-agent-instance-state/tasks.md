## 1. Verified-Self Runtime Authority

- [x] 1.1 Add confined runtime-manifest identity parsing for self operations
- [x] 1.2 Verify opaque agent id, project, runtime binding, live state, and registry generation
- [x] 1.3 Cross-check tmux bindings when present without requiring tmux for supported headless runtimes
- [x] 1.4 Reject copied pointers, stale generations, ambiguous identities, and unmanaged callers
- [x] 1.5 Add tmux, headless, stale-manifest, and adversarial identity tests

## 2. Canonical Instance-State Store

- [x] 2.1 Add `.houmao/memory/agents/<agent-id>/state.sqlite` paths and versioned schema
- [x] 2.2 Add store identity, deployment, instance-contract digest, and launch-attempt metadata
- [x] 2.3 Add explicit state database migration and integrity checks
- [x] 2.4 Integrate journaled `preparing`, `prepared`, `starting`, `active`, and `failed` launch states
- [x] 2.5 Revalidate and reuse compatible preserved-instance state
- [x] 2.6 Add failure-injection and preserved-instance lifecycle tests

## 3. Runtime Variables

- [x] 3.1 Extend instance-contract models with typed runtime-variable declarations and consumers
- [x] 3.2 Add launch value collection, defaults, validation, and revision-one initialization
- [x] 3.3 Render prompt and memo consumers from one launch snapshot
- [x] 3.4 Add verified-self list, get, and explain commands
- [x] 3.5 Add explicit-target admin compare-and-set mutation and revision history
- [x] 3.6 Reject secret-bearing declarations and mutations
- [x] 3.7 Add isolation, relaunch, snapshot, mutation, and no-implicit-prompt tests

## 4. Named Mindsets

- [x] 4.1 Extend instance-contract models with mindset declarations, stable question ids, bounds, and skill bindings
- [x] 4.2 Initialize every declared mindset at fresh launch and preserve compatible revisions on relaunch
- [x] 4.3 Add one-transaction immutable snapshots for all mindsets required by one skill
- [x] 4.4 Add explicit-target admin inspection and optimistic revision mutation
- [x] 4.5 Validate low-authority content and reject tool, gate, instruction, credential, or evidence authority
- [x] 4.6 Validate bound static-skill snapshot instructions without claiming runtime interception
- [x] 4.7 Add manual and implicit skill behavior cases for successful and fail-closed mindset lookup

## 5. Deployment, Routing, and Verification

- [x] 5.1 Preserve exact instance-contract declarations and digest through deployment
- [x] 5.2 Block incompatible deployment updates while live or preserved instances reference the old digest
- [x] 5.3 Update admin, agent, shared-routines, and agent-instance skill routing
- [x] 5.4 Update generated prompts and runtime-state documentation
- [x] 5.5 Run focused suites plus project format, lint, typecheck, and unit tests
- [x] 5.6 Build and check distributions and run strict OpenSpec validation
