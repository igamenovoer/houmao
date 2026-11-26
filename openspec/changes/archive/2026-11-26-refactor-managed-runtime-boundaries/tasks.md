# Tasks

## 1. Required Startup and Rollback

- [x] 1.1 Give `start_runtime_session` a required-startup commit point and track exact ownership for resources as they are acquired. Fault-inject controller construction and manifest-write failures after backend creation. Verify cleanup of the newly owned backend and observer and retry after the error is corrected.
- [x] 1.2 Withdraw partial required gateway and registry publication under the attempt's owner and generation before releasing the evidence needed to fence cleanup. Fault-inject publication after manifest creation, exercise a competing generation, and verify that operator-owned paths, preexisting resources, authorization history, and the shared tmux server are preserved.
- [x] 1.3 Cover manager and passive headless launch failure propagation while retaining passive external registry authority and the optional auto-attach partial-start contract. Verify an already-started agent remains usable when the optional attach fails.

## 2. Typed Launch Result and Owner Operation Validation

- [x] 2.1 Return the verified launch completion from the shared project launch service. Use it for Click rendering and owner v1 serialization. Compare the existing CLI JSON, stdio result fields, and Web/terminal handoff across the normal entrypoints. Keep locator recovery behavior covered.
- [x] 2.2 Report an optional gateway auto-attach failure through the completed owner v1 result with the live identity and existing error field. Test the stdio path, publication of the caller locator, and exit status 2 after the partial result on both CLI paths. Verify one launch call and update the execution and CLI references for this outcome.
- [x] 2.3 Use typed operation arguments and a shared read-only decision before owner setup. Remove Click option introspection and repeated operation rules at that boundary. Test defaults and argument validation, cleanup dry runs, scope and generation checks, and refusal before setup for invalid or read-only requests. Verify admitted transport failures still report uncertainty without replay.

## 3. Backend Capabilities

- [x] 3.1 Resolve shared gateway capability facts from the existing backend kind and run-mode data. Use one query at attach validation, both launch modes, and service startup. Test parser-backed TUI, Web, Hermes TUI, service, and headless behavior. Cover omitted and explicit timing values separately for manager launch, direct runtime launch, attach, and the gateway process while preserving persisted desired timings and the existing status and error behavior.
- [x] 3.2 Reuse the same capability facts where newly supported backend classification is repeated in runtime and gateway selection. Verify the current launch, resume, and attach matrix for DSH and Hermes, including passive headless launch and backend-specific authorization.

## 4. Filesystem Mailbox State

- [x] 4.1 Route move, archive, and ordinary mark through one transaction for local message flags and unread-summary updates. Verify that archiving the only unread message decrements the count, move-to-archive and retry agree, unrelated flags stay intact, and ordinary mark uses the same count rule.
- [x] 4.2 Preserve canonical and shared projection ordering, lock discipline, and current SQLite schema. Test a failed local update after the shared move followed by retry. Verify recomputing a stale summary from retained rows preserves existing mailbox flags.

## 5. Managed TUI Observation

- [x] 5.1 After the manual adoption cutoff, share detector eligibility and version-aware parser invocation across manager/gateway single-session observation, passive observation, and the retained server poll. Test below-floor, missing, unparseable, and qualified metadata through their actual entrypaths. Include a version above the qualified-through point within an open-ended registry range.
- [x] 5.2 Cover the same existing diagnostic shape, selected profile provenance, and unavailable parsed surface on unsupported versions. Verify exact pane and generation, per-caller lifecycle and hook rules, and structured native observations for Hermes TUI and Web.

## 6. Hermes Durable Receipt Validation

- [x] 6.1 Use the existing Hermes TUI receipt model and shared identity check for both readers. Test valid terminal and queued receipts, malformed evidence, and an incomplete matching terminal receipt. Verify the incomplete receipt leaves the prompt slot unresolved without replay, while valid attributable terminal evidence settles the exact request.

## 7. Passive Client Transport

- [x] 7.1 Extract shared transport for pair detection and the maintained passive client. Replace old client inheritance and move the supported inherited operations to the passive surface. Test accepted and refused pair authorities, normalized result models, refresh refusals, and raw stdout and stderr text artifacts.
- [x] 7.2 Verify the existing concrete client constructor, endpoint signatures, auth challenge and signed request binding, timeouts, redirect and TLS handling, and response limits. Cover selected-agent signed requests with the existing passive API and preserve the documented response model imports.

## 8. Integrated Verification

- [x] 8.1 Run the focused runtime registry and gateway, execution-owner, mailbox, detector, Hermes, and passive client suites. Exercise launch and control through the manager, delegated stdio, and passive API. Clear `TMUX` and `TMUX_PANE` and use an isolated tmux server for checks that start tmux.
- [x] 8.2 Run `pixi run lint`, `pixi run typecheck`, `pixi run test`, and strict OpenSpec validation. Compare representative existing CLI, HTTP, v1, and persisted shapes against the compatibility baseline.
