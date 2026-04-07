## Context

The current skill assets under `src/houmao/agents/assets/system_skills/` now use a three-way boundary for communication-related work:

- `houmao-agent-messaging` selects the communication lane and discovers mailbox posture through `agents mail resolve-live`
- `houmao-agent-email-comms` owns ordinary mailbox operations and transport-aware fallback
- `houmao-process-emails-via-gateway` owns one notifier-driven unread-email round

The synced main specs do not fully match that boundary. `houmao-agent-messaging-skill` still describes direct ownership of ordinary mailbox commands, and `houmao-agent-gateway-skill` still names retired split mailbox skills as delegation targets. The docs-oriented specs also still summarize the boundary with broader mailbox wording than the implemented skill text.

## Goals / Non-Goals

**Goals:**
- Make the main OpenSpec requirements match the implemented skill boundary.
- Keep `houmao-agent-messaging` defined as a discovery-and-handoff router for mailbox work.
- Keep `houmao-agent-email-comms` as the single ordinary mailbox operations skill.
- Remove retired mailbox skill names from any remaining synced spec requirements.

**Non-Goals:**
- Changing runtime behavior, installer behavior, or CLI surfaces.
- Redesigning the mailbox skill family beyond the current implemented split.
- Reworking broader mailbox or gateway protocols.

## Decisions

### Keep the correction as a spec-alignment change
This change updates existing capabilities instead of introducing a new one.

Why:
- The repo already implements the new boundary in skill content.
- The mismatch is between current requirements and current implementation, not between desired and existing product behavior.

Alternative considered:
- Treat the mailbox handoff boundary as a new capability. Rejected because no new product surface is being introduced.

### Define `houmao-agent-messaging` mailbox coverage as discovery plus handoff
The messaging skill spec should name `agents mail resolve-live` as the mailbox-facing discovery surface and define mailbox work as handoff to the dedicated mailbox skills.

Why:
- That matches the current top-level skill and action pages.
- It removes ambiguity about whether `houmao-agent-messaging` is allowed to duplicate ordinary mailbox operation guidance.

Alternative considered:
- Keep `houmao-agent-messaging` as a co-owner of mailbox operations. Rejected because it reintroduces overlap with `houmao-agent-email-comms`.

### Keep gateway delegation pointed at the current mailbox skill family only
The gateway skill spec should delegate mailbox work to `houmao-agent-email-comms` and `houmao-process-emails-via-gateway`, not to removed split mailbox skills.

Why:
- The split mailbox skills are no longer current installed skill names.
- The gateway skill should describe the currently supported follow-on skill names only.

Alternative considered:
- Leave retired names in the spec as compatibility history. Rejected because synced main specs are normative, not archival notes.

### Align README and CLI-reference specs with the narrower router wording
The docs specs should use “mailbox routing” or equivalent wording for `houmao-agent-messaging`, while reserving ordinary mailbox operations for `houmao-agent-email-comms`.

Why:
- The docs should not teach readers that the generic messaging skill owns mailbox execution details.
- The wording needs to match the system skill pages the docs summarize.

Alternative considered:
- Leave the broad mailbox wording in docs specs as harmless shorthand. Rejected because it creates the same ambiguity that the skill edit just removed.

## Risks / Trade-offs

- [Risk] The wording change may look cosmetic and be under-scoped in implementation. → Mitigation: define explicit requirement updates for supported surfaces, routing language, and stale mailbox skill names.
- [Risk] Narrowing `houmao-agent-messaging` too far could imply it no longer participates in mailbox discovery. → Mitigation: keep `agents mail resolve-live` and mailbox lane selection explicitly in scope.
- [Risk] Docs specs may drift again if a future skill refactor changes routing words without syncing requirements. → Mitigation: make the boundary explicit in both skill-facing and docs-facing requirements.
