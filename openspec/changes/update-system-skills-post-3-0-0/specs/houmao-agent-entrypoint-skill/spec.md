# Spec Delta

## ADDED Requirements

### Requirement: Agent entrypoint routes post-3.0.0 agent-facing surfaces accurately
`houmao-agent-entrypoint` SHALL update its `When to Route Here` descriptions for `agent-access` (`default-group`, `managed-self`), `agent-messaging` (`request` vs `prompt`, `houmao-cccc`), `agent-gateway` (`houmao-cccc`, `open-browser`), `agent-email-comms`, and `agent-inspect` (usage records).

#### Scenario: Managed agent routes request, CCCC, or usage queries accurately
- **WHEN** a verified managed agent invokes `houmao-agent-entrypoint` for peer work requests, `houmao-cccc` queues, `managed-self` keys, or turn usage
- **THEN** the `## Subcommands` table directs the turn to the exact owning `houmao-shared-routines` child
- **AND THEN** `When to Route Here` distinguishes attributed `request` from verbatim `prompt` and `houmao-cccc` chat from Houmao mail

### Requirement: Agent entrypoint consolidates overlapping eligibility and help contracts
`houmao-agent-entrypoint` SHALL merge overlapping prose across `## Actor and Target Contract`, `## Ineligible Routes`, and `## Help Contract` in `SKILL.md` into a concise eligibility matrix while keeping `## Workflow` and `## Guardrails` compliant with `imsight-agent-skill-handling`.

#### Scenario: Eligibility rules are expressed once concisely
- **WHEN** a reviewer inspects `houmao-agent-entrypoint/SKILL.md`
- **THEN** help behavior, fresh identity verification, and admin-route rejection appear without multi-section prose repetition

### Requirement: Agent entrypoint preserves info-before-identity and fresh self verification
`houmao-agent-entrypoint` SHALL preserve `narrow-implicit` activation, informational help before `agents self identity`, fresh `houmao-mgr --print-json agents self identity` before every operational route, immutable `actor_kind=agent`, admin-route rejection, and non-collapsing `pro`/`lite`.

#### Scenario: Help request avoids identity probing while operational route verifies fresh identity
- **WHEN** a managed agent sends a pure help request versus an operational request
- **THEN** help answers read-only without running `agents self identity`
- **AND THEN** any operational route runs fresh `agents self identity` without reusing cached identity and rejects `project-mgr`, `credential-mgr`, `agent-definition`, `specialist-mgr`, `operator-messaging`, and `welcome`
