## ADDED Requirements

### Requirement: Profile-backed launch applies memo seeds before session publication
When a managed launch is started from a reusable launch profile that stores a memo seed, the runtime SHALL apply the memo seed after resolving the managed-agent identity and memo paths and before publishing or starting the runtime session.

The seed target SHALL be the resolved `houmao-memo.md` and contained `pages/` directory for the authoritative agent id and active project overlay.

For policy `initialize`, the runtime SHALL apply the seed only when `houmao-memo.md` is missing or empty and `pages/` is missing or empty. If either target already contains content, the runtime SHALL leave both memo and pages unchanged and SHALL report that the memo seed was skipped.

For policy `replace`, the runtime SHALL replace `houmao-memo.md` and the contained `pages/` tree with the seed content before the provider starts.

For policy `fail-if-nonempty`, the runtime SHALL fail launch before provider startup when the target memo or pages already contain content.

The runtime SHALL NOT apply a memo seed to direct launches that do not resolve a stored launch profile.

#### Scenario: Initialize seed writes before startup
- **WHEN** launch profile `researcher` stores memo seed policy `initialize`
- **AND WHEN** managed agent `researcher` has an empty memo file and no pages
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao writes the seeded memo content and pages before starting the provider runtime
- **AND THEN** the managed prompt header points at a memo file that already contains the seeded content

#### Scenario: Initialize seed preserves existing memo state
- **WHEN** launch profile `researcher` stores memo seed policy `initialize`
- **AND WHEN** managed agent `researcher` already has non-empty `houmao-memo.md`
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao leaves both the memo file and pages unchanged
- **AND THEN** launch output reports that the memo seed was skipped because existing memo state was present

#### Scenario: Replace seed rewrites memo state
- **WHEN** launch profile `demo` stores memo seed policy `replace`
- **AND WHEN** managed agent `demo` already has memo and page content
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao replaces the memo and contained pages with the stored memo seed content before provider startup

#### Scenario: Fail-if-nonempty aborts before provider startup
- **WHEN** launch profile `strict` stores memo seed policy `fail-if-nonempty`
- **AND WHEN** managed agent `strict` already has one page under `pages/`
- **AND WHEN** an operator launches from that profile
- **THEN** the launch fails before provider startup
- **AND THEN** the existing memo and pages remain unchanged

#### Scenario: Direct launch does not apply profile memo seed
- **WHEN** a launch profile exists with a memo seed
- **AND WHEN** an operator launches the same recipe directly without selecting that profile
- **THEN** Houmao does not apply the stored profile memo seed
