## Context

The earlier late-mailbox-registration change introduced a conservative rule: joined sessions whose relaunch posture is unavailable are rejected up front for mailbox registration. That matched the old activation model where long-lived TUI sessions needed relaunch before mailbox-related work could become live.

The later tmux live-mailbox-binding change replaced that old activation model for tmux-backed sessions. Runtime-owned mailbox mutation now updates both durable manifest state and the targeted `AGENTSYS_MAILBOX_*` projection in tmux session environment, which is the live mailbox authority for subsequent mailbox work. The runtime, mailbox prompts, skills, and gateway notifier all already depend on that live tmux projection rather than the provider process's inherited launch-time env snapshot.

That leaves one stale guard in place: joined tmux sessions adopted without structured relaunch options still fail late mailbox registration solely because `agent_launch_authority.posture_kind == "unavailable"`, even though Houmao still owns the session manifest, the attached tmux session, and the live mailbox projection for that session. The result is a contract split where ordinary tmux-backed sessions can become mailbox-active without relaunch, while joined tmux sessions with the same live authority are blocked for historical reasons unrelated to mailbox actionability.

## Goals / Non-Goals

**Goals:**
- Allow joined tmux-backed sessions without relaunch posture to late-register and late-unregister mailbox support when Houmao can safely update both durable mailbox state and the owning tmux live mailbox projection.
- Align mailbox activation-state reporting, mailbox CLI behavior, and gateway mail-notifier readiness with the tmux live-mailbox contract already implemented for supported tmux-backed sessions.
- Keep the joined-session relaunch contract unchanged: non-relaunchable joined sessions remain non-relaunchable even if they become mailbox-active.
- Eliminate the spec and documentation conflict where join flows are described as supported mailbox workflows while the mailbox-registration capability still normatively rejects them.
- Ensure expected mailbox-management and gateway-notifier command failures surface as clean `houmao-mgr` CLI errors rather than Python tracebacks.

**Non-Goals:**
- Inventing relaunch authority for joined sessions that were adopted without launch options.
- Changing server-backed mailbox registration support; this remains a local managed-agent workflow.
- Reworking mailbox transport lifecycle semantics outside the joined-session eligibility rule.
- Normalizing arbitrary unexpected internal exceptions into friendly output; unexpected faults may still surface with developer-oriented failure behavior outside the expected operator-error contract.

## Decisions

### Decision: Separate relaunch authority from mailbox-mutation authority

The stale rejection path assumes that a session must be relaunchable in order to mutate mailbox state safely. That is no longer true for tmux-backed joined sessions.

For mailbox mutation, the relevant safety question is narrower:

- can Houmao persist the updated mailbox binding in the session manifest,
- can Houmao refresh or clear the targeted mailbox projection in the owning tmux session environment,
- can Houmao keep those two updates coherent for subsequent mailbox work.

If those conditions hold, joined-session relaunch unavailability SHALL NOT by itself block late mailbox registration or unregistration.

Alternative considered:
- Keep using relaunch posture as the mailbox-registration gate.
  Rejected because the runtime no longer relies on relaunch to make tmux-backed mailbox mutation actionable, so this gate preserves an obsolete coupling between restartability and mailbox liveliness.

### Decision: Treat joined tmux sessions as part of the supported tmux-backed activation path

Joined tmux sessions that successfully refresh the live mailbox projection should follow the same activation model as other supported tmux-backed sessions:

- mailbox mutation succeeds,
- tmux live mailbox projection is refreshed,
- activation state is `active`,
- runtime-owned `agents mail ...` and gateway mail-notifier flows can proceed.

The old `unsupported_joined_session` posture should be removed as a mailbox-registration outcome for local joined tmux sessions whose live mailbox projection can be updated safely. If a required live refresh cannot be completed, the mutation should fail explicitly rather than silently leaving the session in a special joined-only unsupported state.

Alternative considered:
- Keep `unsupported_joined_session` but allow gateway notifier or prompts to work through a separate exception path.
  Rejected because it would preserve two competing mailbox contracts for the same joined runtime posture.

### Decision: Keep failure atomic around durable mailbox state and live tmux projection

Joined sessions should reuse the existing mailbox-mutation transaction shape already used for supported tmux-backed sessions:

- derive the updated launch plan,
- refresh the targeted tmux live mailbox projection,
- refresh backend launch-plan state,
- persist the manifest only after those steps succeed.

If refreshing the tmux live mailbox projection fails, the mutation should fail and retain the prior durable mailbox state. Joined sessions should not gain a new partial-success mode merely because they remain non-relaunchable.

Alternative considered:
- Allow partial success for joined sessions by persisting the mailbox binding even when live projection refresh fails.
  Rejected because it would reintroduce the stale durable-vs-live split that the tmux live-binding change was meant to remove.

### Decision: Gateway notifier support depends on mailbox actionability, not relaunchability

Gateway notifier support already depends on durable mailbox presence plus live mailbox actionability. This change should make that rule explicit for joined tmux sessions:

- if a joined session has a durable mailbox binding and an actionable tmux live mailbox projection, notifier support is available,
- if live mailbox actionability is missing or broken, notifier enablement fails explicitly,
- relaunch posture is irrelevant unless notifier support actually requires relaunch, which it no longer does for tmux-backed mailbox refresh.

Alternative considered:
- Keep notifier support blocked for joined sessions without relaunch posture.
  Rejected because notifier readiness is already defined in terms of live mailbox actionability, and relaunch posture is not part of that contract.

### Decision: Normalize expected mailbox-related CLI failures at the top-level wrapper

The HTT run showed that mailbox register and gateway mail-notifier failures can still print full Python tracebacks when expected operator-facing exceptions escape the command handlers. The command surface should preserve explicit failure semantics without exposing Python stack traces for those ordinary error cases.

The native CLI contract for this change should therefore require:

- mailbox-related command handlers continue to raise explicit Click-style operator errors,
- the top-level `houmao-mgr` wrapper normalizes those expected errors into standard CLI failure output even though it runs Click with `standalone_mode=False`,
- unexpected non-Click internal faults are not silently flattened into misleading operator guidance.

That keeps developer debugging behavior for genuine bugs while fixing the mailbox/notifier user experience exposed by the HTT run.

Alternative considered:
- Fix each mailbox and notifier subcommand locally while leaving the top-level wrapper untouched.
  Rejected because the observed failure seam is shared wrapper behavior, and patching individual commands would leave the CLI contract inconsistent and brittle.

## Risks / Trade-offs

- [Joined-session mailbox mutation could be attempted for targets Houmao cannot safely mutate] → Keep the change scoped to locally controlled joined tmux sessions that still have manifest-backed controller authority and a reachable owning tmux session.
- [Specs may continue to drift because mailbox activation rules are spread across multiple capabilities] → Update the mailbox-registration, runtime, and notifier specs together in the same change so activation, readiness, and operator workflow stay aligned.
- [Operators may assume mailbox activation also makes joined sessions relaunchable] → Preserve explicit docs and runtime behavior that mailbox activation does not create relaunch authority.
- [Existing tests may only cover ordinary local interactive sessions] → Add joined-session regression coverage at the runtime, managed-agent CLI, and notifier-readiness levels.
- [CLI error normalization could accidentally swallow unexpected faults] → Limit the friendly-error contract to expected Click/operator failures and keep regression tests that distinguish those from unhandled internal exceptions.

## Migration Plan

1. Remove the joined-session mailbox-registration guard that keys only on `session_origin == joined_tmux` plus `posture_kind == unavailable`.
2. Reuse the existing tmux live-mailbox refresh path for joined-session mailbox register and unregister flows.
3. Update activation-state reporting so joined tmux sessions report `active` after a successful live refresh rather than `unsupported_joined_session`.
4. Update gateway notifier readiness tests and docs to treat joined tmux sessions as supported when the live mailbox projection is actionable.
5. Update the top-level `houmao-mgr` wrapper tests so expected mailbox/notifier failures render as clean CLI errors without Python tracebacks.
6. Verify with a real joined TUI session that `agents mailbox register`, `agents mail status`, and `agents gateway mail-notifier status|enable` work without relaunch and fail cleanly when they should.

Rollback is straightforward: restore the joined-session guard and the prior spec wording that rejects joined sessions without relaunch posture.

## Open Questions

None. The required behavior is already implied by the tmux live-mailbox design; this change is the missing contract alignment.
