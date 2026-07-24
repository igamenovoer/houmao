## 1. Definition and Deployment Contracts

- [x] 1.1 Extend instance-contract models with optional private workspace contracts and semantic labels
- [x] 1.2 Model activation mode, default selection, and workdir mode independently
- [x] 1.3 Preserve workspace selection and contract digest through Deployment Request, Plan, and Agent Deployment
- [x] 1.4 Reject unknown activation features, unsafe root policies, and in-use contract updates
- [x] 1.5 Add definition and deployment contract tests

## 2. TOML and SQLite Workspace State

- [x] 2.1 Add `houmao-agent-workspace.toml` models for stable identity, topology, bindings, tracking, and index locator
- [x] 2.2 Reject mutable SQLite digests, generations, and growing record inventories in TOML
- [x] 2.3 Add `houmao-agent-workspace.sqlite` schema for workspace identity, generation, records, payloads, and projections
- [x] 2.4 Cross-validate TOML and SQLite workspace identity
- [x] 2.5 Add semantic binding confinement, path-kind, collision, and optimistic mutation validation
- [x] 2.6 Add schema, drift, and path-safety tests

## 3. Recoverable Launch Preparation

- [x] 3.1 Add unique project-contained private-root allocation
- [x] 3.2 Integrate idempotent workspace preparation into canonical launch-attempt state
- [x] 3.3 Create staged TOML, SQLite, required paths, and instance association before process start
- [x] 3.4 Resolve execution workdir independently as project root or private root
- [x] 3.5 Revalidate and reuse compatible preserved workspaces
- [x] 3.6 Preserve failed-attempt evidence and clean only safe operation-owned staging
- [x] 3.7 Add process-start, collision, preservation, and workdir-mode tests

## 4. Git Posture and Workspace Operations

- [x] 4.1 Add owned `.git/info/exclude` entry management for local-untracked posture
- [x] 4.2 Block local-untracked mode for indexed content without altering repository history
- [x] 4.3 Add explicit tracked-permitted transition without staging or committing
- [x] 4.4 Add explicit-target inspect, validate, remap, materialize, doctor, and cleanup commands
- [x] 4.5 Add verified-self read-only semantic path resolution
- [x] 4.6 Add immutable mindset projection and workspace-index integration
- [x] 4.7 Add drift-checked preservation and destructive-cleanup tests

## 5. Skills, Documentation, and Verification

- [x] 5.1 Update admin, agent, shared-routines, and agent-instance routing
- [x] 5.2 Keep custom private workspaces separate from `houmao-utils-workspace-mgr`
- [x] 5.3 Add UC-05 manual and implicit behavior cases
- [x] 5.4 Document auxiliary storage, TOML/SQLite authority, semantic paths, and Git posture
- [x] 5.5 Run focused suites plus project format, lint, typecheck, and unit tests
- [x] 5.6 Build and check distributions and run strict OpenSpec validation
