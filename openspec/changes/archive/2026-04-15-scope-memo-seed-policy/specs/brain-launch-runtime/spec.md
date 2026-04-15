## MODIFIED Requirements

### Requirement: Profile-backed launch applies memo seeds before session publication
When a managed launch is started from a reusable launch profile that stores a memo seed, the runtime SHALL apply the memo seed after resolving the managed-agent identity and memo paths and before publishing or starting the runtime session.

The seed target SHALL be the resolved `houmao-memo.md` and contained `pages/` directory for the authoritative agent id and active project overlay.

The runtime SHALL derive the seed application scope from the stored seed source:

- inline text and file memo seeds SHALL represent `houmao-memo.md`,
- directory memo seeds SHALL represent `houmao-memo.md` only when the seed directory contains `houmao-memo.md`,
- directory memo seeds SHALL represent pages only when the seed directory contains `pages/`.

For policy `initialize`, the runtime SHALL inspect only represented targets and SHALL apply the seed only when each represented target is empty. If any represented target already contains content, the runtime SHALL leave represented and omitted targets unchanged and SHALL report that the memo seed was skipped.

For policy `replace`, the runtime SHALL replace only represented targets with the seed content before the provider starts. A represented memo target SHALL be written to the seed memo text, including empty text. A represented pages target SHALL clear then rewrite the contained `pages/` tree from the seed pages, including clearing pages when the seed contains an empty `pages/` directory.

For policy `fail-if-nonempty`, the runtime SHALL fail launch before provider startup when any represented target already contains content. Omitted targets SHALL NOT cause failure and SHALL remain unchanged.

The runtime SHALL NOT apply a memo seed to direct launches that do not resolve a stored launch profile.

#### Scenario: Initialize memo-only seed ignores existing pages
- **WHEN** launch profile `researcher` stores memo-only seed policy `initialize`
- **AND WHEN** managed agent `researcher` has an empty memo file and existing page content under `pages/`
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao writes the seeded memo content before starting the provider runtime
- **AND THEN** the existing pages remain unchanged

#### Scenario: Initialize multi-component seed skips when represented pages are nonempty
- **WHEN** launch profile `researcher` stores directory seed policy `initialize`
- **AND WHEN** the directory seed contains both `houmao-memo.md` and `pages/`
- **AND WHEN** managed agent `researcher` has an empty memo file and existing page content under `pages/`
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao leaves both the memo file and pages unchanged
- **AND THEN** launch output reports that the memo seed was skipped because represented target state is present

#### Scenario: Replace memo-only seed preserves pages
- **WHEN** launch profile `demo` stores memo-only seed policy `replace`
- **AND WHEN** managed agent `demo` already has memo and page content
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao replaces `houmao-memo.md` with the stored memo seed content before provider startup
- **AND THEN** Houmao leaves the contained pages unchanged

#### Scenario: Replace empty memo seed clears only memo
- **WHEN** launch profile `demo` stores memo seed text `""` with policy `replace`
- **AND WHEN** managed agent `demo` already has memo and page content
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao writes an empty `houmao-memo.md`
- **AND THEN** Houmao leaves the contained pages unchanged

#### Scenario: Replace empty pages seed clears only pages
- **WHEN** launch profile `demo` stores directory seed policy `replace`
- **AND WHEN** the directory seed contains an empty `pages/` directory and no `houmao-memo.md`
- **AND WHEN** managed agent `demo` already has memo and page content
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao clears the contained pages
- **AND THEN** Houmao leaves `houmao-memo.md` unchanged

#### Scenario: Fail-if-nonempty memo-only seed ignores existing pages
- **WHEN** launch profile `strict` stores memo-only seed policy `fail-if-nonempty`
- **AND WHEN** managed agent `strict` has an empty memo file and one page under `pages/`
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao writes the seeded memo content before provider startup
- **AND THEN** the existing page remains unchanged

#### Scenario: Fail-if-nonempty pages seed aborts on existing pages
- **WHEN** launch profile `strict` stores pages-only directory seed policy `fail-if-nonempty`
- **AND WHEN** managed agent `strict` already has one page under `pages/`
- **AND WHEN** an operator launches from that profile
- **THEN** the launch fails before provider startup
- **AND THEN** the existing memo and pages remain unchanged

#### Scenario: Direct launch does not apply profile memo seed
- **WHEN** a launch profile exists with a memo seed
- **AND WHEN** an operator launches the same recipe directly without selecting that profile
- **THEN** Houmao does not apply the stored profile memo seed
