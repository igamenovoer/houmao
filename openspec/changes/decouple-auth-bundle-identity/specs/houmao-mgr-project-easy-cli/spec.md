## ADDED Requirements

### Requirement: `project easy` auth relationships resolve through auth profile identity
`houmao-mgr project easy` SHALL resolve specialist-selected auth and easy-profile auth overrides through auth profile identity rather than through auth display-name text or auth projection path names as the authoritative key.

`project easy specialist create --credential <name>` SHALL continue to accept a display name for auth selection or creation.

When `--credential` is omitted, the existing `<specialist-name>-creds` behavior SHALL remain as a display-name default only.

Easy-specialist inspection and easy-profile-backed launch SHALL render or accept current auth display names while preserving the underlying auth-profile relationship across auth rename.

#### Scenario: Specialist get renders the current auth display name after rename
- **WHEN** specialist `reviewer` references one auth profile whose display name was changed from `reviewer-creds` to `reviewer-breakglass`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name reviewer`
- **THEN** the command reports `reviewer-breakglass` as the specialist's selected auth name
- **AND THEN** it does not require specialist recreation only because the auth profile was renamed

#### Scenario: Easy-profile-backed launch still resolves the same auth profile after rename
- **WHEN** easy profile `alice` stores an auth override referencing one auth profile currently named `alice-creds`
- **AND WHEN** that auth profile is renamed to `alice-breakglass`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice`
- **THEN** the launch still resolves the same underlying auth profile
- **AND THEN** the launch does not fail only because the stored auth relationship outlived a display-name change
