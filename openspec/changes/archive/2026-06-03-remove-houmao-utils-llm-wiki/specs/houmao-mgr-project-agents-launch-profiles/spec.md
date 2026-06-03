## MODIFIED Requirements

### Requirement: `internals native-agent launch-dossiers` stores explicit managed system-skill policy
`houmao-mgr internals native-agent launch-dossiers add` and `houmao-mgr internals native-agent launch-dossiers set` SHALL accept managed system-skill policy options for native launch dossiers.

The accepted options SHALL include repeatable `--system-skill-set <set>`, repeatable `--system-skill <skill>`, `--system-skills-mode inherit|extend|replace|none`, `--no-system-skills`, and the patch-only clear option `--clear-system-skills`.

When a launch-profile command receives one or more system-skill selectors without an explicit mode, it SHALL store additive mode over the source recipe policy.

`launch-profiles get --name <profile>` SHALL report stored managed system-skill policy separately from project registered/private skill overlays.

#### Scenario: Add stores additive utility skill policy
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name researcher-workspace --recipe researcher-codex-default --system-skill houmao-utils-workspace-mgr`
- **THEN** the command creates an explicit launch profile with additive managed system-skill policy
- **AND THEN** the projected launch-profile YAML records that policy under profile defaults

#### Scenario: Set stores exact all policy
- **WHEN** explicit launch profile `researcher` already exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name researcher --system-skills-mode replace --system-skill-set all`
- **THEN** the stored launch profile records exact replacement mode with set `all`
- **AND THEN** future launches from that profile install the system-skill selection resolved from `all`

#### Scenario: Set clears stored policy back to inherit
- **WHEN** explicit launch profile `researcher` stores disabled system-skill policy
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name researcher --clear-system-skills`
- **THEN** the stored launch profile no longer records explicit system-skill policy
- **AND THEN** future launches from that profile inherit the source recipe policy

#### Scenario: Mutually exclusive system-skill flags fail
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name researcher --no-system-skills --system-skill houmao-utils-workspace-mgr`
- **THEN** the command fails before updating the launch profile
- **AND THEN** the error explains that disabled mode cannot be combined with explicit system-skill selectors

#### Scenario: Removed system-skill selector fails
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name researcher-wiki --recipe researcher-codex-default --system-skill houmao-utils-llm-wiki`
- **THEN** the command fails before writing the launch profile
- **AND THEN** the error identifies `houmao-utils-llm-wiki` as an unknown system skill
