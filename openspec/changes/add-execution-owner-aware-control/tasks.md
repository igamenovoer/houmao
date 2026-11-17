# Tasks

## 1. Execution Contracts and Trusted Configuration

- [x] 1.1 Add strict versioned execution-profile, observed-binding, controller-scope, and context-qualified-path models under `src/houmao/execution/`; verify valid transport variants and rejection of unknown fields, unsafe selectors, and embedded delegation commands with focused unit tests.
- [x] 1.2 Implement operator-owned profile loading through the shared Houmao config root, keeping target project assets and transport credentials outside the profile payload; verify project/agent content cannot supply routes and missing profiles fail before effects.
- [x] 1.3 Define the finite stdio request/response contract, shared size/depth limits, operation capabilities, correlation IDs, deadline budgets, and rejected/indeterminate outcomes; verify malformed/version-mismatched/oversized requests are rejected and serialized diagnostics omit secrets.
- [x] 1.4 Create the execution-context reference under `docs/reference/run-phase/` covering profile format, external prerequisites, account versus credential identity, and initial operation limits; verify examples against the new model schemas and link it from the maintained CLI reference.

## 2. Owner Admission and Launch Preparation

- [x] 2.1 Implement observed owner/context discovery, atomic context-ID initialization on admitted mutation, and fixed-policy controller admission; verify UID/GID/context mismatches and out-of-scope operations fail, while read-only discovery leaves an uninitialized context untouched.
- [x] 2.2 Add `houmao-mgr internals executor serve-stdio` and shared application dispatch around existing launch/control services without duplicate backend runtimes or testing CLI runners; verify protocol stdout framing, stderr diagnostics, and current-account operation results.
- [x] 2.3 Add project launch `--executor`, dispatch before overlay/catalog/credential/home preparation, and defer target-sensitive Click path checks; verify target-only paths, selected-source validation, omitted-executor local behavior, and absence of caller-local launch effects.
- [x] 2.4 Resolve owner identity environment, target roots, bare environment references, and explicit launch values inside the owner context; verify caller roots/auth/delegation selectors are excluded and document target-relative path and environment semantics in the launch reference.

## 3. Persisted Ownership and Explicit Tmux Authority

- [x] 3.1 Persist execution bindings and explicit tmux socket authority through launch plans, strict manifests, owner lifecycle records, resume, and relaunch; update their schema resources and repository fixtures, and verify round trips, stopped-state preservation, and unsupported old-state errors.
- [x] 3.2 Thread recorded server selection through command-based tmux calls, buffer loading, libtmux construction, and generated owner helper invocations; verify explicit sockets override inherited TMUX/TMUX_PANE and no production cleanup uses server destruction or a default-server fallback.
- [x] 3.3 Update gateway/discovery, current-session join, pane-cwd lookup, and controller reconstruction to use captured socket and exact handles; verify same-name isolated servers, replaced-generation rejection, and preservation of unrelated sessions with focused integration coverage.
- [x] 3.4 Document manifest/binding ownership, current-account socket capture, delegated socket defaults, and tmux-safe teardown in lifecycle and registry references; verify documented fields match the schema and tmux examples always select the intended server.

## 4. Passwordless Linux-Account Execution

- [x] 4.1 Add opt-in integration fixtures under `tests/integration/execution/` for temporary operator/owner accounts, external test state, validated restricted sudo policy, and unique isolated tmux sockets; verify fixture cleanup removes only its recorded users, policy paths, PIDs, and resources, including on failure.
- [x] 4.2 Implement non-interactive sudo transport to the fixed owner entrypoint with sanitized environment and no password or root fallback; verify allowed designated accounts succeed and unconfigured accounts/commands or revoked delegation fail without runtime mutation.
- [x] 4.3 Run real differing-UID launch/control tests with target-only project/workdir and selected credentials; verify effective UID/GID, file ownership/permissions, HOME/environment, exact tmux routing, and exclusion of operator delegation material from the harness.
- [x] 4.4 Document administrator prerequisites and a restricted delegation example using a trusted installed helper/policy; verify it with the temporary non-root operator rather than relying on the development user's unrestricted sudo, and record the actual commands/results.

## 5. Operator Locators and Registry Discovery

- [x] 5.1 Add the distinct `executor_agents/` schema and atomic secret-free locator storage, with lexical-only removal and owner-binding conflict checks; verify foreign paths/endpoints remain metadata and local stale cleanup preserves execution locators.
- [x] 5.2 Extend shared managed-target resolution to combine owner-local records and execution locators before communication-only imports, preserving explicit `--port` bypass; verify exact-ID routing, equivalent-record deduplication, name ambiguity, conflicting bindings, and no caller-local probes for delegated targets.
- [x] 5.3 Publish locators after admitted birth and implement `admin executors reconcile`/`forget`; inject operator publication failure and verify partial success, explicit binding-checked recovery, no repeated birth, and preservation of owner state on forget.
- [x] 5.4 Add bounded owner-observed lifecycle listing and context/authority output; verify active-only behavior, lifecycle-inclusive unavailable targets, no false stopped classification, and unchanged communication-only lifecycle restrictions.
- [x] 5.5 Update registry layout, resolution/ownership, cleanup, and CLI references for executor locators and recovery commands; verify examples show context-qualified foreign paths and local cleanup never infers remote liveness.

## 6. Execution-Bound Lifecycle and Native Refresh

- [x] 6.1 Route finite state/inspect, resume, prompt, interrupt, stop, relaunch, and supported gateway/selected-agent cleanup through the bound owner; verify active/degraded/stale/stopped paths reuse owner authority, stop preserves relaunch locators, and unsupported terminal/streaming operations fail explicitly.
- [x] 6.2 Route `home`, `refresh --check`, and refresh through the same owner binding, including context-qualified JSON/plain output; verify inspection causes no home/material/registry repair and refresh preserves its no-restart/no-reprojection contract.
- [x] 6.3 Enforce pinned-route and owner-generation admission around mutations, and distinguish pre-admission failures from lost/oversized post-admission results; verify profile retargeting, context replacement, concurrent relaunch, deadline/disconnect, and no automatic mutation replay or local/server fallback.
- [x] 6.4 Extend lifecycle, native-refresh, and CLI references with executor capability errors, owner-qualified cleanup, lost-response inspection, and context mismatch recovery; verify the documented finite commands against the Linux-account integration fixture.

## 7. SSH and Container Execution

- [x] 7.1 Implement fixed-command OpenSSH transport with batch authentication, established host-key verification, no PTY/agent forwarding, and JSON-only variable inputs; verify argv/remote-command handling, unsupported versions, transport failures, and secret-free results with focused tests.
- [x] 7.2 Add a fixture-owned SSH daemon and temporary keys/known-hosts state outside the checkout; run actual launch/inspect/stop/relaunch through the stdio helper in a target-only project and verify owner identity, saved-route reuse, host/context mismatch rejection, and clean fixture-only teardown.
- [x] 7.3 Implement Docker exec transport into an existing container with pinned full container ID and configured user; verify native argv, target-only paths, replaced-container rejection, capability errors, and no container creation, socket forwarding, or implicit runtime fallback.
- [x] 7.5 Complete the execution/backend/operation support matrix and SSH/container setup documentation with actual host qualification evidence, explicitly deferred Docker qualification, and unsupported combinations; verify no examples rely on caller-local remote paths, new public HTTP authority, or implicit asset deployment.

## 8. Cross-Context Acceptance and Repository Checks

- [x] 8.1 Run combined acceptance with two same-user agents using distinct supported private-key references and separate homes, plus a different-UID owner; verify sibling bindings/sessions survive refresh/relaunch/stop, same-name caller sessions remain untouched, and communication-only imports never gain lifecycle authority.
- [x] 8.2 Qualify native DSH ACP/Web owner-context flows through the maintained fixture workflow with an explicit case/model and unattended operation; reuse existing backend evidence and run a focused non-DSH owner-routing smoke where needed, recording skipped/unsupported behavior accurately without ambient credentials.
- [ ] 8.3 Run `pixi run test`, relevant execution/runtime integration suites, lint, formatting checks, strict type checking, documentation build, distribution/schema-resource checks, and `openspec validate add-execution-owner-aware-control --strict`; deliver a requirement-to-evidence acceptance map and verify the required Linux-account/SSH routes have passing evidence; Docker qualification is deferred by user instruction before marking the change complete.

## Workflow Follow-up

- Qualify the Docker transport against a prepared test container before claiming live container support verified. The user explicitly deferred this qualification on 2026-11-17 and directed current work to host execution.
