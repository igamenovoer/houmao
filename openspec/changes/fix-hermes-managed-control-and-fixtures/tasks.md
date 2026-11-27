# Tasks

## 1. Hermes TUI Manager Prompt Admission

- [x] 1.1 Add a structured Hermes TUI branch at the shared manager prompt entrypoint. Reuse the existing owner slot and pass the original claim to native submission. Test a ready pinned conversation with the terminal parser disabled, refusal before input on busy or unavailable authority, and a manager and gateway competing for one unresolved slot.
- [x] 1.2 Reuse the native receipt wait after admission and map the existing manager result fields from the typed receipt. Test one native submission and exact settlement with the gateway absent, queued acceptance after a human turn wins, and wrong or lost evidence leaving the original attempt recoverable. Cover both the direct wait and the shorter delegated execution budget.
- [x] 1.3 Document Hermes TUI readiness, independent terminal attachment, and manager receipt outcomes. Compare the documented results with direct and delegated command tests for attached, detached, and different displayed conversations.

## 2. Detached Hermes Self Verification and Gateway Proof

- [x] 2.1 Bind owner-private daemon evidence and the managed-home locator to the exact published Hermes service or TUI generation. Test ordinary launch, supported same-home adoption without Houmao environment variables, and a stale writer trying to publish after replacement. Verify that a reused daemon cannot carry older work across the proof boundary.
- [x] 2.2 Resolve detached Hermes self before interpreting tmux hints. Reuse normal manifest and registry checks, then verify the recorded daemon and caller lineage. Test real child-process resolution for both modes and refusal for a copied locator, wrong home, replaced or stale daemon, stale generation, and unsafe evidence. Recheck managed tmux, Web, and headless self paths.
- [x] 2.3 Use current Hermes daemon liveness for managed-self key loading and receiving ingress. Verify signed self mailbox discovery and authorized operations for a detached viewer, refusal for stale enrollment or daemon evidence, and no unsigned retry. Document detached self targeting in the manager and Hermes references.

## 3. Manager Fixture Reconciliation and Errors

- [x] 3.1 Reconcile manager fixture prompt and stop against the captured runtime in its own registry. Test an existing stopped run followed by a same-runtime relaunch, prompt, stop, and idempotent second stop. Exercise a reused ID, missing authority, and a concurrent generation change before mutation. Keep offline inspection and raw and passive fixture behavior covered.
- [x] 3.2 Return the manager exit code and exact saved diagnostic path in fixture error JSON. Keep diagnostic allocation unique, private, and redacted. Test nonzero manager results with and without parseable stdout, and verify that prompt and credential values are absent from public errors.
- [x] 3.3 Preserve the captured launch identity when the initial prompt fails. Test a failed prompt after birth and a partial launch response, verifying that teardown remains scoped to the captured runtime and that the original diagnostic and run evidence remain accessible. Describe recovery and diagnostic fields in the fixture guide.

## 4. Integrated Qualification

- [x] 4.1 Align the Hermes instructional checks with the actual native control and fixture results, including where state and per-request evidence are reported. Run the TUI control and detachment case and the offline and online mailbox round trips using explicit model and service fixtures. Clear inherited tmux variables and use isolated sockets. Record unavailable live prerequisites separately from passing checks.
- [x] 4.2 Run the focused manager, owner-admission, Hermes, gateway proof, mailbox, and fixture suites with the new regressions. Run `pixi run lint`, `pixi run typecheck`, `pixi run test`, and strict OpenSpec validation.
