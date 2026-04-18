## MODIFIED Requirements

### Requirement: Launch profiles capture durable birth-time launch defaults
Launch profiles SHALL support durable birth-time launch defaults without embedding secrets inline.

At minimum, the shared model SHALL support:
- source reference
- managed-agent identity defaults
- working directory
- auth override by reference
- model override by name
- normalized reasoning override by level `1..10`
- operator prompt-mode override
- durable non-secret env records
- declarative mailbox configuration
- launch posture such as headless or gateway defaults
- prompt overlay
- optional gateway mail-notifier appendix default

Prompt overlay SHALL support at minimum:
- `append`, which appends profile-owned prompt text after the source role prompt
- `replace`, which replaces the source role prompt with profile-owned prompt text

The gateway mail-notifier appendix default SHALL be treated as reusable birth-time launch configuration. It SHALL NOT by itself enable the notifier, set notifier mode, or set notifier interval.

#### Scenario: Launch-profile inspection reports stored birth-time defaults
- **WHEN** profile `alice` stores default agent name, workdir, auth override, model override `gpt-5.4-mini`, reasoning level `4`, mailbox config, gateway posture, and gateway mail-notifier appendix default
- **AND WHEN** an operator inspects that profile
- **THEN** the inspection output reports those stored launch defaults as profile-owned configuration
- **AND THEN** the output does not expose secret credential values inline

#### Scenario: Launch-profile stores notifier appendix without forcing notifier enablement
- **WHEN** profile `alice` stores gateway mail-notifier appendix default `Watch billing-related inbox items first.`
- **AND WHEN** an operator inspects that profile
- **THEN** the profile reports that stored appendix default
- **AND THEN** the stored profile does not imply that gateway mail-notifier polling is already enabled for future launches
