# Initialize A Pairwise Loop Run

Use this page when the user already has one authored pairwise plan and needs the canonical `initialize` action: notifier preflight plus the participant preparation wave before the master trigger.

## Workflow

1. Resolve the canonical plan entrypoint and the target `run_id`.
2. Confirm that the plan already defines:
   - the designated master
   - the participant set
   - one standalone preparation brief for each participant
   - the intended preparation posture
3. Verify the participant set against the authored preparation material. If any participant lacks a standalone brief, return to the authoring lane before continuing.
4. Verify or enable gateway mail-notifier behavior for every participating agent through `houmao-agent-gateway` before the run starts.
5. Choose preparation posture:
   - default `fire_and_proceed`
   - optional `require_ack`
6. Send one standalone preparation email to each participant through the owned mailbox surfaces:
   - include only that participant's own role, resources, delegation authority, obligations, forbidden actions, and optional timeout-watch policy
   - do not assume the participant already knows which upstream participant may later contact it
7. Match operator-origin reply policy to the preparation posture:
   - `fire_and_proceed` -> `reply_policy=none`
   - `require_ack` -> `reply_policy=operator_mailbox`
8. When acknowledgement is required, instruct participants to reply to `HOUMAO-operator@houmao.localhost` and review those replies through the reserved operator mailbox before the master trigger is sent.
9. Track the observed initialization state explicitly:
   - enter `initializing` when notifier preflight or preparation delivery is still in progress
   - enter `awaiting_ack` only when `require_ack` is active and required replies are still outstanding
   - enter `ready` only after the preparation wave is complete and any required acknowledgements have arrived
10. Keep the preparation wave separate from the master trigger. This page handles `initialize`; it does not itself perform `start`.

## Preparation Mail Contract

Each preparation mail should make these items easy to find:

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
- Default `fire_and_proceed` initialization may move directly from `initializing` to `ready`.
- Acknowledgement-gated initialization may remain in `awaiting_ack` until the required replies arrive.
- `ready` means the operator may proceed to `start`.

## Guardrails

- Do not send one shared upstream-aware participant matrix as the only preparation artifact.
- Do not ask the participant to infer hidden upstream message shapes during preparation.
- Do not trigger the master before the preparation wave is complete.
- Do not require acknowledgement by default.
