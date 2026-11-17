# Tasks

## 1. Establish the Predecessor and Web Contract Baseline

- [x] 1.1 Confirm change 01 is implemented, accepted, and synchronized, then run its focused DSH regression suite against the pinned source/executable build; record the predecessor and matching build identities before extending runtime assets.
- [x] 1.2 Add controlled-runtime conformance tests for authenticated Web connections, live-agent identity, native idle/maintenance claims, pending-input operations, input/turn receipts, and pre-activation recovery; verify each chosen native service against the pinned DSH revision.
- [x] 1.3 Publish the Web compatibility reference and scenario acceptance map, including the distinction between native behavior and Houmao's conditional admission; verify every delta scenario has a planned evidence source.

## 2. Add Web Surfaces and Managed Lifecycle

- [x] 2.1 Add `dsh_web` and typed terminal/Web native-surface metadata to launch, manifest, registry/discovery, gateway, and managed-state models; verify schemas and serialization distinguish human interface from supervisor metadata without changing existing terminal-provider semantics.
- [x] 2.2 Resolve DSH's existing `tui`/non-headless posture to Web and preserve explicit headless ACP selection; verify project/profile, manager, launch-override, and capability tests cover both selections and reject terminal-only controls.
- [x] 2.3 Implement the owned local Web supervisor with isolated profile, explicit loopback listener, actual bound-port discovery, sanitized startup output, and required companion/build checks. Reject adoption of externally launched hosts; verify refusal leaves them unchanged, alongside startup rollback, port conflicts, missing companion, and two-host isolation with controlled processes.
- [x] 2.4 Implement explicit native session creation/restore and persisted host/agent incarnation binding; verify browser-target identity, stop/detach/relaunch boundaries, exact continuation, and no implicit cold activation from status or ordinary input. Verify reconnection and gateway attachment to an existing owned host preserve its binding without restart, retargeting, or input replay.
- [x] 2.5 Document launch/profile fields, browser entry, native session selection, supervisory logs, and the first-release launch-ownership boundary. Verify examples reject joining manually started Web Hosts, allow verified reconnection to owned hosts, and expose only token-free location/identity metadata without a terminal-parser promise.

## 3. Implement Authenticated Native Managed Admission

- [x] 3.1 Extend the packaged DSH companion with versioned owner-authorized managed description/state/prompt/receipt/interrupt operations; verify missing, revoked, non-owner, wrong-session, and incompatible-protocol requests fail without native mutation.
- [x] 3.2 Implement final deadline, caller-lifetime, execution-incarnation, true-idle, pending-input, and interaction-wait checks at one synchronous native ready-only handoff; verify controlled human-first and program-first races, active maintenance, unknown state, and duplicate operation IDs.
- [x] 3.3 Map explicit `ready_only`, `if_no_pending`, and `always` policies and ready-only reset constraints; verify operator queueing works only when selected, structural refusals remain enforced, and ordinary plugin/mail delivery never selects forced queueing or steering.
- [x] 3.4 Implement metadata-only admission receipts and exact native input/turn correlation; verify lost-response reconciliation is read-only, receipt lookup retains no executable prompt payload, and request retries never create a second insertion.
- [x] 3.5 Document internal native admission and operator-policy semantics; verify examples distinguish insertion acknowledgement, active work, terminal outcome, explicit native queues, and ordinary refusal.

## 4. Add the Web API Adapter and Shared Observation

- [x] 4.1 Implement independent `/connect` credentials, cookie/stream ownership, capability/identity validation, and default `interactions=none`; verify browser credentials stay independent, API revocation closes control, and reconnect never repeats a mutation.
- [x] 4.2 Implement native state/history/follow consumption, baseline/sequence reconciliation, freshness checks, and bounded state history; verify gap recovery, repeated events, unavailable authority, and browser-origin activity without terminal or DOM scraping.
- [x] 4.3 Project native active/last turn, pending inbox, blocked questions, model changes, and mixed-input associations into semantic events/state; verify local browser drafts are not fabricated as native pending/typing state and subsequent human work is not assigned by wait timing alone.
- [x] 4.4 Implement explicit turn/incarnation-targeted operator interruption and attempt-scoped abandonment; verify a human-started turn can be intentionally interrupted, late cancellation cannot affect a later human turn, and retained inbox contents remain visible.
- [x] 4.5 Implement no-replay failure/recovery, including native host replacement and pre-activation abandoned-input cleanup; verify death before/after admission, response loss, explicit relaunch, preserved human/operator-queued input, and refusal when safe reconciliation cannot be proven.
- [x] 4.6 Document shared-session control, human approval behavior, interruption scope, and uncertain outcomes; verify the operator guide uses supported read-only recovery and explicit lifecycle actions without automatic resend instructions.

## 5. Integrate Gateway and Passive-Server Projections

- [x] 5.1 Add the DSH Web gateway execution adapter and Web state/history capabilities; verify immediate ordinary-event refusal, active native guards, generation changes, explicit operator policies, and unsupported terminal routes.
- [x] 5.2 Extend passive-server discovery/observer selection and compact/detail/history unions for Web; verify a supervisor tmux pane creates no terminal parser, native Web state is queryable, and stale/unreachable sources fail unavailable rather than retaining idle readiness.
- [x] 5.3 Wire safe gateway-backed and direct fallback observation using the same Web detail contract; verify backing-source changes preserve identity and never launch or resume a cold native agent for inspection.
- [x] 5.4 Extend stale-controller manifest preservation for Web endpoints, native sessions, and incarnation tokens; verify gateway attach/detach, status, and passive-server refresh cannot overwrite newer live state.
- [x] 5.5 Update gateway, managed-state, capability, and troubleshooting references; verify documentation distinguishes Web native state from terminal-only capture, raw-key, parser, and timing surfaces.

## 6. Preserve Accounting and Existing Integrations

- [x] 6.1 Reuse the DSH journal collector for direct human turns and correlate managed input claims before finalization; verify native-observed records, mixed-input single charging, separate human follow-ups, and actual browser-selected provider/model attribution.
- [x] 6.2 Verify accounting continuity across API replay, gateway restart, and explicit host relaunch; assert original generation/cutoffs, immutable final records, inherited-history exclusion, and no duplicate API/journal observations, then document Web accounting scope.
- [x] 6.3 Exercise mailbox reminders, owner-bound CCCC/plugin dispatch, and common semantic event/AG-UI consumers against controlled Web agents; verify shared identity, ordinary admission, periodic reminders, and existing transport selection without terminal assumptions.

## 7. Qualify Browser and Programmatic Coexistence

- [x] 7.1 Extend existing fixture preparation for DSH `mode=tui` raw and managed Web lanes using the same generic cases as headless; verify explicit protocol/model/auth resolution, external private roots, unattended defaults, and fresh-host cloud setup without local models or auth JSON.
- [x] 7.2 Add Playwright coverage using the existing Bun toolchain and a real DSH Web Host with a controlled model; verify native browser/API prompt alternation, shared history/progress, browser navigation isolation, human questions, queued input, and interruption in the same bound session.
- [x] 7.3 Add deterministic browser/API race and failure qualification for both admission orders, lost receipts, revoked credentials, active maintenance, host/agent replacement, and pending-input recovery; verify no refused or abandoned ordinary input executes after recovery.
- [x] 7.4 Extend `skillset/dev/houmao-dev-launch-agents/`, fixture docs, and qualification instructions with token-safe browser sign-in and mixed-control workflows; verify the documented commands target the same native session and distinguish `as_is` human tests from unattended defaults.
- [x] 7.5 Run the opt-in live DeepSeek Web smoke and configured self-hosted lanes where available; record actual build/model/protocol/browser/API evidence and human-origin usage, with explicit not-run limits and no credentials, screenshots containing secrets, or private transcripts in tracked reports.

## 8. Complete Sequential Acceptance

- [x] 8.1 Run focused runtime/gateway/passive-server/browser regressions and required `pixi run format`, `pixi run lint`, `pixi run typecheck`, and `pixi run test`; verify both DSH modes and existing terminal providers remain correct.
- [x] 8.2 Run distribution/resource checks, strict docs build, local-link and secret audits, and OpenSpec validation; verify companion assets ship and no reference checkout, auth state, signed browser URL, or private live artifacts enter the distribution or tracked files.
- [x] 8.3 Finish both scenario acceptance maps and the implementation-time roadmap/#74 completion evidence; verify both ordered changes meet acceptance before recommending issue closure.

## Workflow Follow-up

- Review, validate, synchronize, and archive change 02 after its acceptance gates pass.
- Close issue #74 and mark the combined roadmap scope done only after both headless and interactive implementations have accepted evidence.
