## MODIFIED Requirements

### Requirement: Build and launch resolution applies launch-profile defaults between recipe defaults and direct overrides
When a launch is started from a reusable launch profile, the build and runtime pipeline SHALL resolve effective launch inputs by applying launch-profile defaults after source recipe defaults and before direct launch-time overrides.

At minimum, the pipeline SHALL allow launch-profile-derived values to influence:
- effective auth selection
- effective model selection
- effective tool/model-relative reasoning preset index
- operator prompt-mode intent
- durable non-secret env records
- declarative mailbox configuration
- managed-agent identity defaults
- gateway mail-notifier appendix default
- launch provenance

The resulting build manifest or runtime launch metadata SHALL preserve profile provenance in a secret-free form sufficient for inspection and replay, including whether the birth-time config came from an easy profile or an explicit launch profile.

When a launch-profile-derived gateway mail-notifier appendix default is present, the launch/runtime pipeline SHALL materialize that value into the runtime-owned gateway notifier state for the new session even if notifier polling starts disabled.

Later live gateway mail-notifier edits SHALL remain runtime-owned and SHALL NOT rewrite the stored launch profile.

#### Scenario: Launch-profile-derived auth and mailbox defaults survive into build and runtime resolution
- **WHEN** a launch profile stores auth override `alice-creds` and declarative mailbox defaults
- **AND WHEN** a managed-agent launch is started from that profile without conflicting direct overrides
- **THEN** brain construction uses `alice-creds` as the effective auth selection
- **AND THEN** the resulting launch pipeline carries the profile-derived mailbox configuration into runtime launch resolution

#### Scenario: Launch-profile-derived notifier appendix seeds runtime gateway notifier state
- **WHEN** a launch profile stores gateway mail-notifier appendix default `Watch billing-related inbox items first.`
- **AND WHEN** a managed-agent launch is started from that profile without conflicting direct overrides
- **THEN** the resulting runtime gateway notifier state stores that appendix text for the new session
- **AND THEN** later live notifier enablement can reuse that runtime-owned appendix value

#### Scenario: Direct launch override still wins over launch-profile-owned workdir
- **WHEN** a launch profile stores working directory `/repos/alice`
- **AND WHEN** the operator launches from that profile with direct workdir override `/tmp/debug`
- **THEN** runtime launch uses `/tmp/debug` as the effective working directory
- **AND THEN** profile provenance still records that the launch originated from the named profile

#### Scenario: Direct launch override wins over launch-profile-owned model
- **WHEN** a launch profile stores model override `gpt-5.4-mini`
- **AND WHEN** the operator launches from that profile with direct override `--model gpt-5.4-nano`
- **THEN** brain construction uses `gpt-5.4-nano` as the effective model
- **AND THEN** profile provenance still records that the launch originated from the named profile

#### Scenario: Direct launch reasoning override wins over launch-profile-owned reasoning
- **WHEN** a launch profile stores reasoning override `2`
- **AND WHEN** the operator launches from that profile with direct override `--reasoning-level 12`
- **THEN** brain construction uses reasoning preset index `12` as the effective launch-owned value before native mapping
- **AND THEN** profile provenance still records that the launch originated from the named profile
