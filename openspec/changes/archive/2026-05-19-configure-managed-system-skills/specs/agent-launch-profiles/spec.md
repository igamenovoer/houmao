## ADDED Requirements

### Requirement: Launch profiles store managed system-skill policy as birth-time configuration
The shared launch-profile object family SHALL support an optional managed system-skill policy as reusable birth-time launch configuration.

That stored policy SHALL support:

- `inherit`, meaning use the effective source specialist or recipe policy,
- `extend`, meaning add named system-skill sets or explicit skills to the effective source policy,
- `replace`, meaning use exactly the named system-skill sets or explicit skills stored on the profile,
- `none`, meaning install no current Houmao-owned system skills for future launches from the profile.

When no system-skill policy is stored on a launch profile, the profile SHALL behave as `inherit`.

Patch mutation SHALL preserve an existing launch-profile system-skill policy when no system-skill field is supplied. Replacement mutation SHALL clear an existing system-skill policy unless the replacement request supplies one. Stored mutation SHALL affect future launches only and SHALL NOT rewrite any live managed-agent instance.

Launch-profile inspection SHALL report the stored system-skill policy when present without expanding secret or credential material.

#### Scenario: Launch profile inspection reports additive policy
- **WHEN** launch profile `researcher-wiki` stores additive system-skill policy for `houmao-utils-llm-wiki`
- **AND WHEN** an operator inspects that profile
- **THEN** the inspection output reports the stored system-skill mode and selected skill name
- **AND THEN** it distinguishes that policy from project registered/private skill overlays

#### Scenario: Patch preserves stored system-skill policy
- **WHEN** launch profile `researcher-wiki` stores additive system-skill policy and workdir `/repos/a`
- **AND WHEN** an operator patches only the workdir to `/repos/b`
- **THEN** the stored launch profile records workdir `/repos/b`
- **AND THEN** the stored system-skill policy remains associated with the profile

#### Scenario: Replacement clears omitted system-skill policy
- **WHEN** launch profile `researcher-wiki` stores additive system-skill policy
- **AND WHEN** an operator replaces `researcher-wiki` in the same profile lane without supplying system-skill policy
- **THEN** the replacement profile no longer stores explicit system-skill policy
- **AND THEN** future launches from that profile inherit the source specialist or recipe policy

#### Scenario: Stored profile policy does not mutate live instances
- **WHEN** managed-agent instance `researcher-1` was launched from profile `researcher-wiki`
- **AND WHEN** an operator changes the stored profile system-skill policy
- **THEN** future launches from the profile use the updated policy
- **AND THEN** live instance `researcher-1` and its existing runtime manifest remain unchanged by that stored-profile mutation
