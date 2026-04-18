## MODIFIED Requirements

### Requirement: `project easy profile create/list/get/remove` manages specialist-backed easy profiles
`houmao-mgr project easy profile create --name <profile> --specialist <specialist>` SHALL persist one reusable easy profile that targets exactly one existing specialist.

Easy profiles SHALL be specialist-backed birth-time launch configuration owned by the easy lane.

`project easy profile create` SHALL accept `--gateway-mail-notifier-appendix-text <text>` to store a reusable notifier appendix default on that easy profile.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, `project easy profile create` SHALL ensure `<cwd>/.houmao` exists before persisting profile state.

`project easy profile list`, `get`, and `remove` SHALL resolve the active overlay through the shared non-creating project-aware resolver and SHALL fail clearly when no active overlay exists.

`project easy profile get --name <profile>` SHALL report the source specialist plus the stored easy-profile launch defaults, including the stored notifier appendix default when present.

`project easy profile remove --name <profile>` SHALL remove only the profile definition and SHALL NOT remove the referenced specialist only because that specialist was the profile source.

#### Scenario: Easy profile create bootstraps the missing overlay on demand
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder`
- **THEN** the command ensures `<cwd>/.houmao` exists before storing the profile
- **AND THEN** the persisted profile lands in the resulting project-local catalog and compatibility projection

#### Scenario: Easy profile create stores notifier appendix default
- **WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder --gateway-mail-notifier-appendix-text "Watch billing-related inbox items first."`
- **THEN** the stored easy profile records that notifier appendix default
- **AND THEN** later `project easy profile get --name alice` reports the stored appendix default

#### Scenario: Easy profile remove preserves the referenced specialist
- **WHEN** easy profile `alice` targets specialist `cuda-coder`
- **AND WHEN** an operator runs `houmao-mgr project easy profile remove --name alice`
- **THEN** the command removes the persisted `alice` profile
- **AND THEN** it does not remove specialist `cuda-coder` only because `alice` referenced it

### Requirement: `project easy profile set` patches specialist-backed easy profiles
`houmao-mgr project easy profile set --name <profile>` SHALL patch one existing specialist-backed easy profile in the active project overlay.

The command SHALL preserve the profile source specialist and SHALL preserve unspecified stored launch defaults.

At minimum, `project easy profile set` SHALL support the same stored launch-default field families as `project agents launch-profiles set`, including managed-agent identity defaults, workdir, auth, memory binding, model, reasoning level, prompt mode, env records, mailbox config, launch posture, managed-header policy, prompt overlay, and gateway mail-notifier appendix default.

The command SHALL expose clear flags for nullable or collection fields where the explicit launch-profile `set` surface already exposes matching clear behavior.

When no requested update or clear flag is supplied, the command SHALL fail clearly without rewriting the profile.

#### Scenario: Easy profile set updates auth without dropping prompt overlay
- **WHEN** easy profile `alice` targets specialist `reviewer` and stores auth override `work` plus prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --auth breakglass`
- **THEN** easy profile `alice` stores auth override `breakglass`
- **AND THEN** easy profile `alice` still stores its prior prompt overlay text

#### Scenario: Easy profile set clears prompt overlay
- **WHEN** easy profile `alice` stores prompt overlay mode `append` with prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --clear-prompt-overlay`
- **THEN** easy profile `alice` no longer stores prompt overlay mode or prompt overlay text
- **AND THEN** future launches from `alice` fall back to the source specialist prompt unless a stronger launch-time prompt override is supplied

#### Scenario: Easy profile set clears notifier appendix default
- **WHEN** easy profile `alice` stores gateway mail-notifier appendix default
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --clear-gateway-mail-notifier-appendix`
- **THEN** easy profile `alice` no longer stores a notifier appendix default
- **AND THEN** future launches from `alice` do not inherit a profile-owned notifier appendix unless another source supplies one

#### Scenario: Easy profile set rejects empty update
- **WHEN** easy profile `alice` exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice` without any update or clear flags
- **THEN** the command fails clearly
- **AND THEN** easy profile `alice` remains unchanged
