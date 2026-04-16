## MODIFIED Requirements

### Requirement: Profile-backed launch applies memo seeds before session publication
When a managed launch is started from a reusable launch profile that stores a memo seed, the runtime SHALL apply the memo seed after resolving the managed-agent identity and memo paths and before publishing or starting the runtime session.

The seed target SHALL be the resolved `houmao-memo.md` and contained `pages/` directory for the authoritative agent id and active project overlay.

The runtime SHALL derive the seed application scope from the stored seed source:

- inline text and file memo seeds SHALL represent `houmao-memo.md`,
- directory memo seeds SHALL represent `houmao-memo.md` only when the seed directory contains `houmao-memo.md`,
- directory memo seeds SHALL represent pages only when the seed directory contains `pages/`.

The runtime SHALL replace only represented targets with the seed content before the provider starts. A represented memo target SHALL be written to the seed memo text, including empty text. A represented pages target SHALL clear then rewrite the contained `pages/` tree from the seed pages, including clearing pages when the seed contains an empty `pages/` directory.

The runtime SHALL NOT inspect omitted targets to decide whether a memo seed may apply. Omitted targets SHALL remain unchanged.

The runtime SHALL NOT apply a memo seed to direct launches that do not resolve a stored launch profile.

#### Scenario: Memo-only seed preserves pages
- **WHEN** launch profile `demo` stores memo-only seed text
- **AND WHEN** managed agent `demo` already has memo and page content
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao replaces `houmao-memo.md` with the stored memo seed content before provider startup
- **AND THEN** Houmao leaves the contained pages unchanged

#### Scenario: Empty memo seed clears only memo
- **WHEN** launch profile `demo` stores memo seed text `""`
- **AND WHEN** managed agent `demo` already has memo and page content
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao writes an empty `houmao-memo.md`
- **AND THEN** Houmao leaves the contained pages unchanged

#### Scenario: Empty pages seed clears only pages
- **WHEN** launch profile `demo` stores a directory seed
- **AND WHEN** the directory seed contains an empty `pages/` directory and no `houmao-memo.md`
- **AND WHEN** managed agent `demo` already has memo and page content
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao clears the contained pages
- **AND THEN** Houmao leaves `houmao-memo.md` unchanged

#### Scenario: Multi-component seed replaces memo and pages
- **WHEN** launch profile `demo` stores a directory seed containing `houmao-memo.md` and `pages/notes/start.md`
- **AND WHEN** managed agent `demo` already has memo and page content
- **AND WHEN** an operator launches from that profile
- **THEN** Houmao replaces `houmao-memo.md` with the seeded memo content
- **AND THEN** Houmao clears and rewrites the contained pages from the seed

#### Scenario: Direct launch does not apply profile memo seed
- **WHEN** a launch profile exists with a memo seed
- **AND WHEN** an operator launches the same recipe directly without selecting that profile
- **THEN** Houmao does not apply the stored profile memo seed
