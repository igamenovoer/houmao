## Context

Houmao already has the normative mailbox rule in place. The mailbox protocol and mailbox registration validation treat ordinary managed-agent addresses as `<agentname>@houmao.localhost` and reserve `HOUMAO-*` mailbox local parts under `houmao.localhost` for Houmao-owned system principals such as `HOUMAO-operator@houmao.localhost`.

The inconsistency is at the integration and guidance layer. `houmao-touring` still shows mailbox examples such as `HOUMAO-research@agents.localhost`, `houmao-mailbox-mgr` does not explicitly teach the reserved-prefix rule during mailbox account creation, and the late managed-agent mailbox binding path still reconstructs an omitted address as `<principal_id>@agents.localhost` instead of reusing the ordinary address derivation helper. That makes the packaged skills and one runtime default path disagree with the mailbox protocol they are supposed to teach.

This change crosses three implementation surfaces:

- runtime-owned late filesystem mailbox binding
- packaged system-skill guidance for mailbox administration
- guided-tour mailbox question wording and examples

## Goals / Non-Goals

**Goals:**

- Make omitted late-binding mailbox addresses follow the same ordinary Houmao mailbox address policy as the rest of the mailbox subsystem.
- Keep the existing split between canonical principal id and ordinary mailbox address clear: `HOUMAO-research` versus `research@houmao.localhost`.
- Ensure packaged mailbox-account creation guidance explains that `HOUMAO-*` mailbox local parts under `houmao.localhost` are reserved.
- Make mailbox examples and prompts recommend `houmao.localhost` when the user has not specified a mailbox domain.

**Non-Goals:**

- Invalidating or migrating existing explicit mailbox addresses that use another valid domain.
- Changing the canonical agent identity or mailbox principal-id namespace away from `HOUMAO-<agentname>`.
- Rewriting every archived or purely historical example under `openspec/changes/archive/`.
- Redesigning the broader mailbox transport model or Stalwart contracts.

## Decisions

### Decision: Preserve the split between mailbox principal id and ordinary mailbox address

Ordinary managed-agent mailbox account creation will continue to use two different but related identifiers:

- principal id: `HOUMAO-<agentname>`
- ordinary default mailbox address: `<agentname>@houmao.localhost`

This keeps the agent/principal namespace stable while reserving `HOUMAO-*` mailbox locals under `houmao.localhost` for Houmao-owned system principals only.

Alternative considered:
- Use `HOUMAO-<agentname>@houmao.localhost` as the ordinary default mailbox address.
- Rejected because it directly conflicts with the existing reserved-namespace policy.

### Decision: Omitted late-binding addresses reuse the shared default-address derivation path

The late filesystem mailbox binding path for existing managed agents should not derive its own legacy address from `principal_id`. Instead, when the caller omits `address`, it should reuse the same ordinary mailbox address derivation logic that already produces `<agentname>@houmao.localhost`.

Alternative considered:
- Keep the current late-binding reconstruction `<principal_id>@agents.localhost` and rely only on skill wording to steer users away from it.
- Rejected because the runtime default would still contradict the guidance and protocol.

### Decision: `houmao.localhost` is the recommended domain only when the user has not chosen another explicit address

The system will recommend `houmao.localhost` for ordinary mailbox account creation when the user or caller has not already supplied a domain. Explicit valid mailbox addresses remain authoritative.

Alternative considered:
- Force every mailbox address onto `houmao.localhost`.
- Rejected because the mailbox protocol already allows explicit valid addresses and this change is about consistent defaults and guidance, not domain lockdown.

### Decision: Explain the reserved-prefix rule at question time, not only in deep reference docs

Mailbox account creation is where users choose address and principal-id values. The packaged mailbox-admin and touring skills should therefore explain the reserved `HOUMAO-*` mailbox-local-part rule directly in those workflows, using examples such as:

- address: `research@houmao.localhost`
- principal id: `HOUMAO-research`

Alternative considered:
- Leave the rule only in protocol and reference documentation.
- Rejected because users encounter the confusing examples during account creation, not after they have already chosen the wrong pattern.

## Risks / Trade-offs

- [Existing tests and docs still assert `agents.localhost` examples] → Update the affected examples and add focused coverage for omitted late-binding addresses.
- [Users may misread the change as “HOUMAO- is banned everywhere”] → Phrase the guidance precisely: the reservation applies to mailbox local parts under `houmao.localhost`, not to canonical principal ids.
- [Operators may think non-`houmao.localhost` explicit addresses are invalid] → Keep the specs explicit that the recommendation applies only when the domain is unspecified.

## Migration Plan

No stored-data migration is required.

1. Update the omitted-address late-binding path so runtime-owned default derivation uses `<agentname>@houmao.localhost`.
2. Update packaged mailbox-admin and touring skill assets to explain the reserved-prefix rule and show the new ordinary examples.
3. Update onboarding, CLI, and mailbox-reference examples that currently teach `HOUMAO-...@agents.localhost` as the ordinary account-creation pattern.
4. Add focused automated coverage around omitted late-binding defaults and reserved-prefix guidance where practical.

Rollback is straightforward: restore the previous late-binding default derivation and the previous skill/doc wording.

## Open Questions

- Should this change sweep every remaining non-normative `agents.localhost` mailbox example in active docs, or only the examples that directly describe mailbox account creation and late binding?
