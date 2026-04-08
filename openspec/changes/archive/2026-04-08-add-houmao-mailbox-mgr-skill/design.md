## Context

Houmao already ships packaged system skills for ordinary mailbox operations (`houmao-agent-email-comms`), notifier-driven mailbox rounds (`houmao-process-emails-via-gateway`), gateway lifecycle (`houmao-agent-gateway`), and broader live-agent lifecycle (`houmao-manage-agent-instance`). At the same time, the maintained CLI already exposes three mailbox-administration seams:

- `houmao-mgr mailbox ...` for arbitrary filesystem mailbox roots,
- `houmao-mgr project mailbox ...` for overlay-local filesystem mailbox roots,
- `houmao-mgr agents mailbox ...` for late filesystem mailbox binding on existing local managed agents.

Those surfaces are operator-facing and maintained, but there is no packaged Houmao-owned skill that routes agents to them. As a result, mailbox bootstrap and lifecycle work remain split across CLI references, quickstart examples, and out-of-scope notes in neighboring skills.

The current packaged-skill catalog also has a weak distinction between `mailbox-core` and `mailbox-full`: both sets currently resolve to the same two skill names. Adding a mailbox-administration skill gives `mailbox-full` a real meaning without changing the narrow notifier/ordinary-mail worker pair in `mailbox-core`.

Constraints:

- The new skill must stay inside the flat `houmao-*` packaged skill layout.
- It should route only to maintained CLI surfaces that already exist in v1.
- It must not blur filesystem mailbox admin with actor-scoped mail follow-up or with Stalwart transport-specific runtime bootstrap.

## Goals / Non-Goals

**Goals:**

- Add a packaged Houmao-owned skill named `houmao-mailbox-mgr`.
- Make that skill the mailbox-administration entrypoint for mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late managed-agent mailbox binding.
- Keep the top-level `SKILL.md` brief and route detailed workflows into action pages.
- Give `mailbox-full` a broader mailbox-admin meaning while preserving `mailbox-core` as the narrow mailbox worker pair.
- Update install/reporting/docs surfaces so the packaged skill inventory and set membership remain coherent.

**Non-Goals:**

- Do not add new mailbox CLI families or change the existing mailbox command semantics.
- Do not move ordinary mailbox send/reply/check/mark-read work out of `houmao-agent-email-comms`.
- Do not move gateway mail-notifier or wakeup behavior out of `houmao-agent-gateway`.
- Do not introduce a new Stalwart mailbox-administration CLI family in this change.
- Do not change the filesystem mailbox transport model, late-binding persistence model, or current mailbox registration semantics.

## Decisions

### Decision: The skill name is `houmao-mailbox-mgr`

The packaged skill will use the exact name `houmao-mailbox-mgr`.

Rationale:

- It matches the user-facing intent of “mailbox management” and mirrors the maintained `houmao-mgr mailbox ...` family closely.
- It stays inside the flat reserved `houmao-*` namespace without needing a new family prefix.

Alternatives considered:

- `houmao-manage-mailbox`: more aligned with the existing `houmao-manage-*` naming family, but weaker at signaling the tight relationship to `houmao-mgr mailbox ...`.
- Folding mailbox admin into `houmao-manage-agent-instance`: rejected because mailbox root lifecycle and mailbox account lifecycle are not agent-instance lifecycle.

### Decision: The skill owns three mailbox-admin lanes, selected by intent and scope

`houmao-mailbox-mgr` will route by mailbox-admin lane:

- arbitrary filesystem mailbox root administration -> `houmao-mgr mailbox ...`
- project overlay mailbox administration -> `houmao-mgr project mailbox ...`
- late managed-agent filesystem mailbox binding -> `houmao-mgr agents mailbox ...`

The top-level skill will first classify intent, then choose the lane, then hand off to one action page.

Rationale:

- These three command families form one operator story: create/validate mailbox authority, register mailbox accounts, then bind a live managed agent when needed.
- Keeping them together gives agents one mailbox-admin entrypoint instead of forcing cross-skill discovery for closely related admin tasks.

Alternatives considered:

- Separate skills for root admin and late managed-agent binding: rejected because `agents mailbox register` is usually downstream of mailbox root bootstrap and uses the same filesystem mailbox lifecycle vocabulary.
- Putting `agents mailbox ...` under `houmao-manage-agent-instance`: rejected because that skill already treats mailbox tasks as out of scope and is centered on live-instance lifecycle rather than mailbox authority.

### Decision: The skill will not own actor-scoped mail or gateway reminder flows

`houmao-mailbox-mgr` will explicitly keep these surfaces out of scope:

- `houmao-mgr agents mail ...`
- shared `/v1/mail/*` workflow
- `houmao-mgr agents gateway mail-notifier ...`
- direct gateway `/v1/mail-notifier` and `/v1/wakeups`

Those remain owned by:

- `houmao-agent-email-comms`
- `houmao-process-emails-via-gateway`
- `houmao-agent-gateway`

Rationale:

- Mailbox administration and mailbox participation are different concerns.
- Keeping those boundaries sharp avoids turning the new skill into a generic “all mail things” skill.

Alternatives considered:

- Make `houmao-mailbox-mgr` a superset mailbox skill covering admin and participation: rejected because it would duplicate the existing ordinary mailbox and notifier-round skill families.

### Decision: Stalwart is a documented boundary, not a peer action lane

The skill will describe Stalwart as a mailbox transport/bootstrap boundary through a reference page, not as a peer `actions/*.md` lane with equivalent admin commands.

The new skill will continue to treat maintained mailbox-admin command surfaces as filesystem-only in v1 for:

- `houmao-mgr mailbox ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr agents mailbox ...`

Rationale:

- The current codebase documents Stalwart mailbox bootstrap as runtime/session provisioning, not as a peer mailbox-admin CLI surface.
- Pretending that Stalwart has the same root/account admin CLI would create a false contract.

Alternatives considered:

- Give Stalwart equal action-page treatment in the new skill: rejected because the maintained CLI does not expose equivalent mailbox-root/account CRUD for Stalwart today.

### Decision: `mailbox-core` stays narrow while `mailbox-full` expands

The packaged set semantics will become:

- `mailbox-core` -> `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`
- `mailbox-full` -> `mailbox-core` pair plus `houmao-mailbox-mgr`

Because managed launch/join and CLI-default install already include `mailbox-full`, the new skill will be available in managed homes and explicit default installs without creating a new top-level set.

Rationale:

- This preserves the current narrow worker-pair meaning for `mailbox-core`.
- It gives `mailbox-full` a meaningful expansion instead of keeping it redundant.
- It keeps mailbox-admin guidance close to the existing mailbox family rather than burying it in `user-control`.

Alternatives considered:

- Put `houmao-mailbox-mgr` into `user-control`: rejected because mailbox admin is more tightly coupled to the mailbox workflow family than to specialists/credentials/definitions.
- Create a new dedicated `mailbox-admin` set and add it everywhere: rejected because the existing `mailbox-full` name already communicates “broader mailbox surface”.

### Decision: The skill tree uses one router plus action/reference pages

The skill tree will follow the existing packaged-skill pattern:

- brief top-level `SKILL.md`
- action pages for root lifecycle, registration lifecycle, inspection, and agent binding
- reference pages for scope, lane selection, and the Stalwart boundary

Representative actions:

- `init`
- `status`
- `register`
- `unregister`
- `repair`
- `cleanup`
- `accounts-list`
- `accounts-get`
- `messages-list`
- `messages-get`
- `agent-binding-status`
- `agent-binding-register`
- `agent-binding-unregister`

Rationale:

- This matches the current skill authoring pattern already used by `houmao-manage-*` and `houmao-agent-*` skills.
- It keeps the entrypoint short while making command-specific guidance discoverable.

## Risks / Trade-offs

- [Skill overlap confusion] -> Keep the top-level scope and routing guidance explicit about what stays in `houmao-agent-email-comms`, `houmao-process-emails-via-gateway`, `houmao-agent-gateway`, and `houmao-manage-agent-instance`.
- [False Stalwart parity] -> Treat Stalwart as a reference/boundary page only and state clearly that the maintained mailbox-admin CLI remains filesystem-only in v1.
- [Install-surface surprise] -> Document clearly that `mailbox-full` now differs from `mailbox-core`, and update `system-skills` CLI/docs so the new inventory and set membership are visible.
- [Doc drift from expanded skill count] -> Update README, system-skills overview, and CLI reference in the same change so the new packaged skill count and set semantics stay synchronized.

## Migration Plan

No data migration is required.

Implementation should:

1. add the packaged skill tree and catalog entry,
2. expand `mailbox-full`,
3. update system-skills reporting/tests for the new inventory and set membership,
4. update docs that enumerate packaged skills or mailbox set semantics.

Rollback is straightforward: remove the packaged skill entry and restore the prior `mailbox-full` membership.

## Open Questions

- None for proposal scope. The change assumes the new skill is documentation/routing over maintained existing CLI surfaces rather than a request to add new mailbox CLI behavior.
