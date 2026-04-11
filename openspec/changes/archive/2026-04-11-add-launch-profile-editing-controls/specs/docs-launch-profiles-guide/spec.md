## ADDED Requirements

### Requirement: Launch-profiles guide distinguishes overrides, patches, and replacements
The launch-profiles guide SHALL distinguish:

- direct launch-time overrides, which affect only one launch and do not rewrite stored launch profiles,
- profile patch commands, which mutate stored reusable defaults while preserving unspecified fields,
- profile replacement commands, which rewrite the same named profile in the same lane and clear omitted optional fields.

The guide SHALL explain that the easy and explicit lanes share one catalog-backed launch-profile family but replacement remains lane-bounded.

#### Scenario: Reader can choose patch versus replacement
- **WHEN** a reader wants to change one stored reusable launch default
- **THEN** the launch-profiles guide directs them to use the appropriate patch command for their lane
- **AND THEN** the guide reserves same-name `create --yes` or `add --yes` for full same-lane replacement

#### Scenario: Reader understands direct launch overrides do not persist
- **WHEN** a reader compares launch-time overrides with stored profile edits
- **THEN** the guide states that direct launch-time overrides affect only the submitted launch
- **AND THEN** the guide states that profile `set` changes future launches from the stored profile
