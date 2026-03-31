## MODIFIED Requirements

### Requirement: Rebrand scope preserves non-targeted public surfaces
The repository SHALL preserve the `Houmao` project and distribution identity and SHALL standardize the active runtime identity and environment namespace on `HOUMAO_*`.

Legacy standalone CLI retirement or other operator-surface cleanup SHALL NOT require another package-namespace rename after this change, because the supported live runtime namespace is already unified on `HOUMAO_*`.

The repository MAY continue to retire deprecated surfaces without redefining the `houmao` package identity away from `Houmao`.

#### Scenario: Active runtime namespace is Houmao-named after the rename
- **WHEN** a maintainer inspects active runtime env contracts and package identity after the namespace rename
- **THEN** the project remains `Houmao`
- **AND THEN** active runtime identity and environment contracts use the `HOUMAO_*` namespace
- **AND THEN** supported-surface cleanup does not preserve `AGENTSYS_*` as the stable live namespace
