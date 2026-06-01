## ADDED Requirements

### Requirement: Packaged catalog includes the operator messaging skill in default control sets
The packaged current-system-skill catalog SHALL include `houmao-operator-messaging` as a current installable Houmao-owned system skill.

That packaged skill SHALL use `houmao-operator-messaging` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `core` named set SHALL include `houmao-operator-messaging` because it is part of the closed operator-control skill surface.

The packaged catalog's `all` named set SHALL include `houmao-operator-messaging` because `all` includes every `core` skill plus packaged utility skills.

The packaged catalog SHALL NOT add a dedicated named set for `houmao-operator-messaging`; the current installable named-set surface SHALL remain `core` and `all`.

Because managed launch and managed join resolve `core`, and CLI-default installation resolves `all`, those fixed auto-install selections SHALL include `houmao-operator-messaging` through existing set membership.

#### Scenario: Maintainer sees operator messaging in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-operator-messaging`
- **AND THEN** the skill uses `houmao-operator-messaging` as its flat packaged asset subpath under the maintained runtime asset root

#### Scenario: Core and all sets expose operator messaging
- **WHEN** a maintainer inspects the packaged `core` and `all` named sets
- **THEN** both sets include `houmao-operator-messaging`
- **AND THEN** no additional operator-messaging-specific named set is present

#### Scenario: Default installs include operator messaging through existing sets
- **WHEN** Houmao resolves packaged skill installation for managed launch, managed join, or CLI-default installation
- **THEN** the resolved install list includes `houmao-operator-messaging`
- **AND THEN** that inclusion comes from the existing `core` or `all` set expansion
