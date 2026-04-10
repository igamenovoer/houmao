## ADDED Requirements

### Requirement: Late filesystem mailbox binding derives omitted addresses from the ordinary Houmao mailbox address policy
When runtime-owned late filesystem mailbox binding derives a mailbox address because the caller omitted `address`, the runtime SHALL derive that address from the ordinary Houmao mailbox address policy rather than by concatenating the canonical mailbox principal id with a legacy domain.

For ordinary managed-agent mailbox bindings, the derived address SHALL use the managed-agent name as the mailbox local part without the `HOUMAO-` principal-id prefix and SHALL use domain `houmao.localhost`.

For the same binding, the derived default mailbox principal id SHALL remain the canonical `HOUMAO-<agentname>` value unless the caller supplies an explicit override.

If the caller supplies an explicit valid mailbox address, the runtime SHALL preserve that explicit address rather than rewriting it to the recommended Houmao default domain.

#### Scenario: Late mailbox binding derives the ordinary Houmao address when address is omitted
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name research --mailbox-root /tmp/shared-mail`
- **AND WHEN** the operator omits both `--address` and `--principal-id`
- **THEN** the resulting late filesystem mailbox binding uses principal id `HOUMAO-research`
- **AND THEN** the resulting mailbox address is `research@houmao.localhost`

#### Scenario: Explicit late-binding address remains authoritative
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name research --mailbox-root /tmp/shared-mail --address review@custom.localhost`
- **THEN** the resulting late filesystem mailbox binding preserves address `review@custom.localhost`
- **AND THEN** the runtime does not rewrite that explicit mailbox address to `research@houmao.localhost`
