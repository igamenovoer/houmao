# Initialize A Pairwise Loop Run

Use this page when the user already has one authored pairwise plan and needs the canonical `initialize` action: notifier preflight plus the targeted participant preparation wave before the master trigger.

## Workflow

1. Resolve the canonical plan entrypoint and the target `run_id`.
2. Confirm that the plan already defines:
   - the designated master
   - the participant set
   - the authored topology or descendant relationships
   - one standalone preparation brief for each participant
   - the preparation target policy
   - the intended preparation posture
3. Verify the participant set against the authored preparation material. If any participant lacks a standalone brief, return to the authoring lane before continuing.
4. Verify the authored topology. If descendant relationships are not clear enough to identify delegating/non-leaf participants, return to the authoring or revision lane before continuing.
5. Resolve the preparation mail recipient set:
   - by default, include only participants that have descendants in the authored topology, meaning participants expected to delegate jobs to other agents
   - exclude leaf participants by default
   - include leaf participants only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set
6. Verify or enable gateway mail-notifier behavior for the targeted preparation recipients through `houmao-agent-gateway` before the run starts.
7. Choose preparation posture:
   - default `fire_and_proceed`
   - optional `require_ack`
8. Send one standalone preparation email to each targeted recipient through the owned mailbox surfaces:
   - include only that participant's own role, resources, delegation authority, obligations, forbidden actions, and optional timeout-watch policy
   - do not assume the participant already knows which upstream participant may later contact it
   - do not send preparation mail to leaf participants that were not explicitly included in the preparation target set
9. Match operator-origin reply policy to the preparation posture:
   - `fire_and_proceed` -> `reply_policy=none`
   - `require_ack` -> `reply_policy=operator_mailbox`
10. When acknowledgement is required, instruct targeted recipients to reply to `HOUMAO-operator@houmao.localhost` and review those replies through the reserved operator mailbox before the master trigger is sent.
11. Track the observed initialization state explicitly:
   - enter `initializing` when notifier preflight or preparation delivery is still in progress
   - enter `awaiting_ack` only when `require_ack` is active and required replies from targeted preparation recipients are still outstanding
   - enter `ready` only after the targeted preparation wave is complete and any required acknowledgements from targeted recipients have arrived
12. Keep the preparation wave separate from the master trigger. This page handles `initialize`; it does not itself perform `start`.

## Preparation Target Policy

Default preparation targets are the delegating/non-leaf participants: participants that have descendants in the authored topology and are expected to delegate jobs to other agents.

Leaf participants are excluded by default. Include leaf participants only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set.

When `require_ack` is active, missing acknowledgements from leaf participants do not block `ready` unless those leaf participants were explicitly included in the preparation target set.

## Preparation Mail Contract

Each preparation mail should make these items easy to find for the targeted recipient:

- `run_id`
- participant identity and role
- local resources or artifacts available to that participant
- allowed delegation targets or allowed delegation set
- delegation-pattern expectations for work categories, when needed
- mailbox, reminder, receipt, or result obligations
- forbidden actions
- reply instructions when acknowledgement is required

## Initialize Contract

- `initialize` is the prestart action, not the master trigger.
- Preparation material may exist for every participant, but preparation mail targets delegating/non-leaf participants by default.
- Default `fire_and_proceed` initialization may move directly from `initializing` to `ready`.
- Acknowledgement-gated initialization may remain in `awaiting_ack` until the required replies from targeted preparation recipients arrive.
- `ready` means the targeted preparation wave is complete and the operator may proceed to `start`.

## Guardrails

- Do not send one shared upstream-aware participant matrix as the only preparation artifact.
- Do not ask the participant to infer hidden upstream message shapes during preparation.
- Do not guess the preparation target set when the topology is unclear; return to authoring or revision first.
- Do not trigger the master before the targeted preparation wave is complete.
- Do not require acknowledgement by default.
- Do not treat `require_ack` as permission to silently widen preparation mail to leaf participants.
