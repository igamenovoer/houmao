## Context

The completed `restore-pairwise-skill-and-add-v2` change split the restored stable pairwise skill from the enriched `houmao-agent-loop-pairwise-v2` skill. The v2 tree currently treats `initialize` as a participant-wide preparation wave: authoring guidance expects standalone participant preparation material, `prestart/prepare-run.md` sends one preparation mail to every participant, `operating/start.md` checks that the full preparation wave completed, and the templates describe a generic participant preparation wave.

The requested follow-on behavior keeps the enriched v2 prestart lane but reduces default mailbox noise. Leaf agents should receive actionable context when a delegating parent actually sends them work, not through an automatic prestart mail. Participants with descendants still need preparation by default because they must understand downstream delegation authority, mailbox/reminder obligations, and result routing before they start dispatching work.

## Goals / Non-Goals

**Goals:**

- Make v2 `initialize` target participants with descendants by default.
- Keep leaf agents out of the preparation-mail target set unless the user explicitly requests leaf preparation.
- Keep participant preparation material available in authored plans so leaf roles and constraints remain explicit.
- Define `require_ack` and `ready` semantics in terms of the targeted preparation recipients.
- Update tests so the packaged v2 skill content locks in the default and explicit override.

**Non-Goals:**

- Change the restored stable `houmao-agent-loop-pairwise` skill.
- Remove v2 `initialize`, prestart guidance, acknowledgement-gated initialization, or canonical observed states.
- Add a runtime graph parser or automatic descendant inference API.
- Force every plan to omit leaf preparation material.

## Decisions

### Decision: Separate preparation material from preparation mail recipients

The v2 plan guidance will continue to support participant preparation material for all participants, but `initialize` will send preparation mail by default only to the preparation target set.

Rationale:

- It preserves explicit plan documentation for leaf participants.
- It avoids making authoring depend on whether the operator later chooses all-participant preparation.
- It keeps implementation as a skill-content change rather than a new data model or runtime feature.

Alternative considered:

- Remove leaf participant preparation material by default. Rejected because it weakens the plan contract and makes later explicit leaf preparation harder to perform consistently.

### Decision: Define the default target set as non-leaf participants with downstream delegation responsibilities

The default preparation target set will be participants that have descendants in the authored topology, meaning participants expected to delegate jobs to other agents. Leaf participants are excluded by default.

Rationale:

- Delegating participants need prestart context before they dispatch work.
- Leaf participants can receive sufficient actionable context from the actual delegated job message.
- The definition matches the user’s wording and stays understandable in skill documentation.

Alternative considered:

- Send only to the designated master by default. Rejected because intermediate delegating participants may also need prestart context before they receive and fan out work.

### Decision: Make leaf preparation an explicit override

The guidance will state that leaf participants are included only when the user explicitly asks to prepare leaf agents, prepare all participants, or names a leaf participant in the preparation target set.

Rationale:

- It keeps the default quiet while preserving the operator’s ability to prepare every participant for sensitive or high-coordination runs.
- It keeps acknowledgement handling predictable because required acknowledgements come from actual preparation recipients.

Alternative considered:

- Infer leaf preparation from `require_ack`. Rejected because acknowledgement posture controls whether targeted recipients must reply; it should not silently widen the recipient set.

## Risks / Trade-offs

- [Ambiguous topology] → If the plan does not make descendant relationships clear enough to identify non-leaf participants, the skill should return to authoring/revision before initialization instead of guessing.
- [Leaf agent lacks context when work arrives] → The delegated job message must carry the actionable leaf context; keep leaf preparation material in the plan so the delegating parent can include that context.
- [Operator expected old all-participant prep behavior] → Document the explicit all-participant or leaf-inclusion override in v2 prestart and template guidance.
- [Acknowledgement confusion] → Define `require_ack` as applying to targeted preparation recipients only unless leaf participants are explicitly included.

## Migration Plan

1. Update v2 top-level and prestart wording to describe targeted preparation recipients.
2. Update authoring references and templates to distinguish participant preparation material from preparation mail targets.
3. Update start/run-charter guidance so `ready` means the targeted preparation wave is complete.
4. Update packaged system-skill tests to assert delegator-default and explicit leaf override wording.

Rollback strategy:

- Revert the v2 skill-content and test changes to return to all-participant preparation mail by default.

## Open Questions

- None. The default target policy and explicit leaf override are defined by the user request.
