# Enhancement Proposal: `mail send --to` Should Require Full Mailbox Addressing

## Status
Resolved on 2026-03-17.

## Resolution Summary
`mail send --to` now requires explicit full mailbox addresses, short names such as `bob` are rejected, and the docs/tests reflect the stricter addressing contract.

## Summary
Tighten the runtime mailbox CLI so `mail send --to <who>` does not accept loose agent names and instead requires a full-form mailbox identity, ideally a full mailbox address such as `AGENTSYS-bob@agents.localhost`.

The current CLI accepts any string for `--to`, and the runtime forwards that value verbatim into the mailbox request payload. That is convenient for demos, but it is ambiguous for a real mailbox system and becomes risky if one agent can own multiple mailboxes or participate in multiple mail groups.

## Why
The current behavior is underspecified:
- `--to bob` is accepted syntactically,
- the runtime does not normalize `bob` into `AGENTSYS-bob` or a full mailbox address,
- managed delivery ultimately depends on exact principal registration and address matching.

That gap is manageable in a simple one-mailbox-per-agent local setup, but it does not scale cleanly:
- one agent may eventually participate in multiple shared mailbox groups,
- one agent may eventually have multiple mailbox addresses or roles,
- ambiguous short names make addressing rules implicit instead of explicit,
- operators and agents cannot tell from the CLI whether a recipient is meant to be a principal id, a mailbox address, or a nickname.

If the long-term mailbox model is meant to support precise addressing, the CLI should enforce that precision instead of silently accepting shorthand.

## Requested Enhancement
1. Change the `mail send --to` contract so the accepted recipient form is explicit and unambiguous.
2. Prefer requiring a full mailbox address such as:
   - `AGENTSYS-bob@agents.localhost`
3. If principal ids remain supported, document them as a distinct accepted form and validate them explicitly rather than accepting arbitrary nicknames.
4. Reject ambiguous short names like:
   - `bob`
   - `alice`
5. Update help text, docs, and examples so users see the full addressing form by default.
6. Add validation errors that explain the expected recipient format clearly.

## Acceptance Criteria
1. `mail send --to bob` fails fast with an explicit validation error.
2. `mail send --to AGENTSYS-bob@agents.localhost` is accepted and follows the normal runtime mailbox flow.
3. If principal ids are still allowed, the allowed format is explicitly documented and validated rather than inferred.
4. Docs and Q&A examples use full-form mailbox identities by default.
5. Tests cover both accepted full-form addressing and rejected shorthand addressing.

## Non-Goals
- No requirement to redesign the canonical mailbox protocol itself.
- No requirement to solve mailbox principal deregistration in the same enhancement.
- No requirement to remove internal principal ids if they are still useful in other layers.

## Suggested Follow-Up
- Decide whether the user-facing CLI should require mailbox addresses only, or allow a strictly validated dual-form contract of `{principal_id | mailbox_address}`.
- Align this with any future shared-resource config work so named shared mail groups and explicit addresses fit together cleanly.
- If multiple mailbox identities per agent are introduced later, keep CLI addressing explicit rather than adding nickname inference.
