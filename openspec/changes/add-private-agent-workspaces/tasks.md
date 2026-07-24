## 1. Definition and Deployment Contracts

- [ ] 1.1 Extend instance-contract models with optional private workspace contracts and semantic labels
- [ ] 1.2 Model activation mode, default selection, and workdir mode independently
- [ ] 1.3 Preserve workspace selection and contract digest through Deployment Request, Plan, and Agent Deployment
- [ ] 1.4 Reject unknown activation features, unsafe root policies, and in-use contract updates
- [ ] 1.5 Add definition and deployment contract tests

## 2. TOML and SQLite Workspace State

- [ ] 2.1 Add `houmao-agent-workspace.toml` models for stable identity, topology, bindings, tracking, and index locator
- [ ] 2.2 Reject mutable SQLite digests, generations, and growing record inventories in TOML
- [ ] 2.3 Add `houmao-agent-workspace.sqlite` schema for workspace identity, generation, records, payloads, and projections
- [ ] 2.4 Cross-validate TOML and SQLite workspace identity
- [ ] 2.5 Add semantic binding confinement, path-kind, collision, and optimistic mutation validation
- [ ] 2.6 Add schema, drift, and path-safety tests

## 3. Recoverable Launch Preparation

- [ ] 3.1 Add unique project-contained private-root allocation
- [ ] 3.2 Integrate idempotent workspace preparation into canonical launch-attempt state
- [ ] 3.3 Create staged TOML, SQLite, required paths, and instance association before process start
- [ ] 3.4 Resolve execution workdir independently as project root or private root
- [ ] 3.5 Revalidate and reuse compatible preserved workspaces
- [ ] 3.6 Preserve failed-attempt evidence and clean only safe operation-owned staging
- [ ] 3.7 Add process-start, collision, preservation, and workdir-mode tests

## 4. Git Posture and Workspace Operations

- [ ] 4.1 Add owned `.git/info/exclude` entry management for local-untracked posture
- [ ] 4.2 Block local-untracked mode for indexed content without altering repository history
- [ ] 4.3 Add explicit tracked-permitted transition without staging or committing
- [ ] 4.4 Add explicit-target inspect, validate, remap, materialize, doctor, and cleanup commands
- [ ] 4.5 Add verified-self read-only semantic path resolution
- [ ] 4.6 Add immutable mindset projection and workspace-index integration
- [ ] 4.7 Add drift-checked preservation and destructive-cleanup tests

## 5. Skills, Documentation, and Verification

- [ ] 5.1 Update admin, agent, shared-routines, and agent-instance routing
- [ ] 5.2 Keep custom private workspaces separate from `houmao-utils-workspace-mgr`
- [ ] 5.3 Add UC-05 manual and implicit behavior cases
- [ ] 5.4 Document auxiliary storage, TOML/SQLite authority, semantic paths, and Git posture
- [ ] 5.5 Run focused suites plus project format, lint, typecheck, and unit tests
- [ ] 5.6 Build and check distributions and run strict OpenSpec validation
