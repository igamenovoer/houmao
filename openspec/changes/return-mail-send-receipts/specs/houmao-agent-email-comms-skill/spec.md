# Spec Delta

## ADDED Requirements

### Requirement: Mail writes use their receipts and read-only follow-ups

The packaged mail guidance SHALL use the first CLI receipt to report a send, reply, or post. It SHALL use `mail peek` for details on the binding that owns the receipt reference and use read-only evidence to reconcile uncertain writes.

#### Scenario: The first write is verified

- **WHEN** a managed agent receives a verified send, reply, or post receipt and only needs confirmation
- **THEN** the skill directs it to report the receipt's status and reference from the first call

#### Scenario: The agent inspects send or reply details

- **WHEN** a managed agent needs more information about a verified send or reply
- **THEN** the skill shows `mail peek --message-ref` on the writing agent's original channel and binding
- **AND THEN** the guidance selects JSON on the first write or the read-only inspection

#### Scenario: The operator inspects a post

- **WHEN** an authorized caller needs more information about a verified post
- **THEN** the skill directs it to peek using the selected recipient's channel, binding, and receipt reference

#### Scenario: A send or reply remains unresolved

- **WHEN** a managed agent receives a submission-only or uncertain send or reply result without a verified reference
- **THEN** the skill directs it to check `mail list --box sent` using the sender's authority and original channel and binding when available
- **AND THEN** it retains an unresolved outcome if the lookup is inconclusive

#### Scenario: An operator post remains unresolved

- **WHEN** an authorized caller needs to reconcile a post with an uncertain outcome
- **THEN** the skill directs it to inspect the same target binding's inbox and archive
- **AND THEN** it retains an unresolved outcome if the lookup is inconclusive
