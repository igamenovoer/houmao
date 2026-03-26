# Feature Request: First-Class Agent Session Resume

## Status
Proposed

## Summary
Add a first-class session resume feature so operators can intentionally continue a previous agent session instead of relying on internal manifest reload behavior.

Today, houmao already has partial resume mechanics under the hood:
- runtime control commands reconstruct a controller from a persisted session manifest,
- local interactive backends reuse the existing tmux-hosted provider TUI,
- resumable headless backends reuse the persisted provider `session_id`,
- some backends, such as `codex_app_server`, explicitly cannot be resumed from persisted state.

That is useful implementation plumbing, but it is not yet a coherent user-facing feature. There is no explicit operator workflow that clearly answers:
- which past sessions are resumable,
- how to intentionally continue one specific prior session,
- what backend-specific guarantees or limitations apply,
- whether the resumed session is expected to reuse the original runtime identity or create a new managed-agent instance.

## Why
Without a first-class resume feature, session continuation is implicit and fragile:
- users have to know that control commands reconstruct state from a saved manifest,
- the entrypoint for continuation is “call another control command on a still-known session” rather than “resume this session,”
- stopped or detached sessions are harder to recover intentionally,
- backend differences are hidden until failure,
- there is no clean operator-facing contract for long-lived agent work that spans multiple terminals, machines, or interruptions.

This becomes more important as houmao grows more managed-agent and gateway workflows. A session-oriented system should make “continue previous work” an explicit capability, not an internal side effect.

## Requested Scope
1. Add an explicit session resume workflow for runtime-owned agent sessions.
2. Define what it means to resume a session for each backend class:
   - local interactive tmux-backed sessions,
   - headless resumable providers,
   - non-resumable backends.
3. Expose resumable-session discovery so operators can identify candidate sessions before resuming.
4. Provide a clear CLI contract for targeting a prior session, for example by:
   - `session_id`,
   - `manifest_path`,
   - `agent_id`,
   - or other explicit resume handle.
5. Define whether resume reuses the existing managed-agent identity or creates a new active runtime record that points at the prior provider session.
6. Surface backend-specific resume limitations and failure reasons clearly in CLI output.
7. Ensure resumed sessions can participate correctly in related capabilities such as:
   - shared registry publication,
   - gateway attach/detach,
   - state/history inspection,
   - stop/cleanup behavior.

## Acceptance Criteria
1. Operators can intentionally request session continuation through an explicit CLI workflow instead of only triggering it indirectly through normal control commands.
2. The system can list or otherwise discover resumable sessions and indicate enough metadata for selection.
3. Resume behavior is documented and backend-specific:
   - tmux-backed local interactive sessions describe reuse of the existing provider surface,
   - headless backends describe reuse of persisted provider session ids,
   - non-resumable backends fail clearly and early.
4. A resumed session has a well-defined identity story for:
   - `agent_id`,
   - `agent_name`,
   - registry record ownership,
   - runtime session id,
   - session manifest path.
5. Gateway-related behavior is defined for resumed sessions so operators know whether a gateway can be reattached, preserved, or must be recreated.
6. Tests cover at least:
   - resuming a local interactive session,
   - resuming a headless provider session,
   - a clear non-resumable backend failure path,
   - registry/state behavior after resume.

## Non-Goals
- No requirement to make every backend resumable.
- No requirement to preserve backward compatibility with older implicit control flows if a cleaner explicit resume contract replaces them.
- No requirement to support arbitrary recovery of corrupted or partially missing runtime artifacts.
- No requirement to solve cross-host migration of live tmux sessions in the same change.

## Suggested Follow-Up
- Create an OpenSpec change that defines the session resume identity model and CLI surface.
- Decide whether resume should be added to `houmao-mgr agents ...`, the lower-level realm controller CLI, or both.
- Define one authoritative resumable-session record format so runtime, registry, and gateway logic all refer to the same session lifecycle contract.
- Document the difference between:
  - reconnecting to an existing local interactive surface,
  - resuming a provider-native headless conversation,
  - reconstructing controller state from persisted artifacts.
