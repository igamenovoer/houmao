## ADDED Requirements

### Requirement: Codex unattended strategies emit final CLI config override surfaces
For Codex unattended launch strategies, the registry-owned startup surface SHALL include final Codex CLI config override arguments for strategy-owned non-secret preferences in addition to any runtime-home config mutations.

The strategy action path SHALL canonicalize conflicting caller launch inputs before emitting those final CLI config overrides, so the final provider start uses the strategy-owned unattended posture even when copied setup config, caller launch overrides, or cwd/project `.codex/config.toml` define conflicting values.

At minimum, Codex unattended strategy final CLI config override emission SHALL cover strategy-owned approval and sandbox posture. It MAY also cover other non-secret strategy-owned Codex startup preferences when the strategy declares ownership for those keys.

#### Scenario: Codex strategy exposes CLI override ownership for startup policy
- **WHEN** a developer inspects a Codex unattended strategy entry
- **THEN** the strategy identifies the CLI config override surfaces it owns for unattended startup policy
- **AND THEN** runtime-home `config.toml` mutation remains documented as fallback and repair state rather than the only authority boundary

#### Scenario: Codex strategy appends final approval and sandbox overrides
- **WHEN** the runtime resolves a compatible Codex unattended strategy
- **AND WHEN** caller launch args include a conflicting Codex `-c approval_policy="on-request"` or `-c sandbox_mode="read-only"` override
- **THEN** the strategy canonicalizes the conflicting caller inputs
- **AND THEN** the final Codex process arguments include strategy-owned CLI config overrides for unattended approval and sandbox posture
- **AND THEN** cwd/project Codex config layers cannot weaken the maintained unattended startup posture

#### Scenario: Codex strategy keeps secrets out of emitted CLI config overrides
- **WHEN** the runtime resolves a Codex unattended strategy for an env-only provider launch
- **THEN** the strategy may emit non-secret CLI config override args needed for startup-policy or provider-selection correctness
- **AND THEN** the strategy does not emit API key values, auth JSON, OAuth tokens, cookies, or bearer tokens in CLI args
