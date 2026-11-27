# Tasks

## 1. Prepare and Resolve the Owner Installation

- [x] 1.1 Qualify stock Hermes v0.23.4 against a test-owned prepared root. Record the actual build, dependency-currency evidence, ready profile discovery and ticket exchange, and the native tool-spawn hook's profile and session context. Check that two native named profiles can use the same prepared dependency selection.
- [x] 1.2 Add trusted execution-owner selection and read-only preflight for the prepared Hermes root, executable, dependency selection, and required capabilities. Verify that missing, stale, unavailable, or incompatible setup produces owner-side instructions before creating a profile or replacing a live worker. Document the explicit owner preparation flow.

## 2. Build and Record Named-Profile Homes

- [x] 2.1 Add the owned profile binding to build and runtime records and create the project-local link to its canonical home. Test unique profile allocation across projects, separate workspaces, rejected unrelated entries and escaping targets, preserved-home reuse, and native home inspection. Document where Hermes state and the project link live.
- [x] 2.2 Stage complete parked profiles before native publication. Project private per-profile model credentials, role, skills, tool settings, and approval inputs. Verify that a pending profile cannot serve halfway through setup, that missing selected credentials fail before readiness, and that rollback leaves an existing profile or project entry intact.

## 3. Run Workers on the Shared Hermes Gateway

- [x] 3.1 Add owner-scoped acquisition and qualification of the shared gateway and profile-qualified native discovery, tickets, and readiness. Test concurrent first launch, wrong root or process identity, wrong profile, an unsupported capability, and profile epoch change under the same gateway PID. Observe that these paths preserve the prepared dependency selection.
- [x] 3.2 Connect Service, TUI, Headless, and the managed launch helper to the canonical named profile and shared host. Verify the exact native session, workspace, and captured authority at normal launch, attachment, and explicit relaunch. Test ACP edit-mode readback, approval-gated commands, pending TUI approval, stale receipts, and correct refusal across profiles. Update the Hermes launch and control references.
- [x] 3.3 Implement exact profile rebind and recovery after a host replacement or independently re-served profile. Verify old authority fails before submission, activated profile configuration is read back, unresolved work retains admission and is never replayed, and sibling profiles keep their own observations.

## 4. Preserve Profile-Scoped Self Access

- [x] 4.1 Ship and qualify the prepared-runtime tool-spawn hook and owner-local proof broker. Test OS peer verification, issuance from the native profile and session context, current generation checks, proof expiry or revocation, and confidentiality in environment handling and diagnostics.
- [x] 4.2 Apply origin verification before selecting the self signer and profile-authority verification at gateway ingress and effect fencing. Test two concurrent signed tool calls, stale and copied selectors, an already admitted effect racing profile retirement, and detached Hermes mail using the exact current identity. Document the supported self caller path.

## 5. Resolve Worker Retirement and Cleanup

- [x] 5.1 Scope stop, retained-home relaunch, and failed-start rollback to the selected profile and its clients. Verify that park and release of the native reservation are distinct checks, and that siblings and the shared gateway survive stop, failure, and force replacement. Cover warm-host reuse after the final worker stops.
- [x] 5.2 Extend authorized explicit cleanup and clean replacement to preview and settle native profile deletion and owned link unlink separately. Test live and retained references, a changed or dangling link, an already absent profile, pending identity settlement, retries, and preserved evidence after incomplete cleanup. Document cleanup and retirement outcomes.
- [x] 5.3 Keep inspection, stop, and explicit cleanup addressable for recorded standalone workers. Test that a request for exact continuation into the named-profile layout fails before retiring a live predecessor. Document fresh launch as the cutover procedure.

## 6. Qualify the Complete Managed Workflow

- [x] 6.1 Update the Hermes fixture and instructional isolation case to share one explicitly selected test-owned execution context across distinct projects while preserving individual workspaces, links, and isolated tmux handles. Check both the fixture's reported bindings and independent native evidence. Verify exact test-host teardown after worker cleanup.
- [x] 6.2 Run the stock Hermes fixture across Service, TUI, and Headless with two live profiles. Correlate the prepared environment, process and receipt evidence to confirm ordinary starts, turns, and relaunches run no dependency installation. Verify distinct credentials and permissions, exact continuation, a signed self mailbox operation, and scoped retirement and cleanup. Record provider build and actual results.
- [x] 6.3 Run focused runtime, launch, permission, authentication, cleanup, and fixture suites, followed by `pixi run lint`, `pixi run typecheck`, `pixi run test`, and strict OpenSpec validation. Record verified results and any unavailable qualification prerequisites.

## Verification

- Stock Hermes v0.23.4 at `8fc0374447313e276f6b9a2764bfc750190c966a` served two named profiles with separate tickets on one gateway. Native profile epochs were qualified through `runtime.describe`. Concurrent local tool runs received the exact native profile and session through the shipped hook. The dependency generation `2161d5d6c6d24705ae764760660e7547` stayed selected and native PM facts retained SHA-256 `8310d6e5caebf230170c631e9c152c51f3674cadd77a912a390c7cd4e0d84cba` across the stock qualification. The read-only owner preflight also left all 124,006 inspected paths unchanged.
- The managed Service, TUI, and Headless fixtures ran concurrently on one exact gateway process and incarnation. Each completed a turn and an exact relaunch, advancing its profile epoch from 1 to 2 and completing a second turn with the same native session. Separate loopback providers verified each profile's synthetic credentials. Native approval readback reported `off` for unattended and `manual` for an `as_is` profile.
- The three-mode campaign retained the same prepared environment, dependency stamp, and PM facts hash. Native PM plugin-check receipts recorded no install or rebuild steps, and the shared gateway log contained no Python dependency or Node preparation. A fresh Headless test confirmed available state and healthy gateway status from the operator shell, using the gateway's unsigned caller policy.
- Two stock Service profiles on the shared host concurrently ran local terminal tools that performed signed `mail.archive` operations. Durable handoff records matched the `self` actor, active generation, signer registration revision, and exact profile authority for each worker. Each archive succeeded and an independent mailbox read confirmed both messages were archived.
- A stock startup failure injected after the client was acquired rolled back the runtime manifest, new profile, project link, and build manifest. Stock `--force clean` removed the predecessor profile and repointed its project link to a fresh profile and session. The sibling's native identity and shared gateway stayed live. Fixture teardown parked the workers and released their reservations. The final managed build sweep removed seven profiles, their project links, and their build manifests with no blocked actions. Independent fixture runs also verified exit of the exact test-owned host.
- The focused runtime, gateway, authentication, cleanup, and fixture suites passed 606 tests. `pixi run --locked lint`, `pixi run --locked typecheck` across 587 source files, and strict OpenSpec validation passed. `pixi run --locked test` passed 6,119 tests with 15 skips and isolated tmux sockets.
