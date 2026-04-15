## ADDED Requirements

### Requirement: Pairwise-v2 initialization treats memo links as authored content
The packaged `houmao-agent-loop-pairwise-v2` initialization guidance SHALL treat initialization memo content as user/LLM-authored Markdown.

When the guidance suggests writing supporting page material under `HOUMAO_AGENT_PAGES_DIR`, it SHALL instruct the agent or operator to add any useful memo link explicitly.

The guidance SHALL NOT rely on a generated memo page index to make supporting pages discoverable.

#### Scenario: Oversized initialization page is linked explicitly
- **WHEN** v2 initialization material is too large for `houmao-memo.md`
- **AND WHEN** the material is placed in a contained page under `HOUMAO_AGENT_PAGES_DIR`
- **THEN** the guidance tells the agent or operator to add a normal Markdown link if that page should be visible from the memo
- **AND THEN** the guidance does not mention waiting for a generated page index

### Requirement: Pairwise-v2 guidance avoids reindex workflow
The packaged `houmao-agent-loop-pairwise-v2` initialization guidance SHALL NOT instruct agents or operators to run a memory reindex command or call a memory reindex endpoint.

#### Scenario: Initialize flow avoids reindex
- **WHEN** a user follows the v2 initialize guidance
- **THEN** the guidance does not include a memory reindex step
- **AND THEN** page discoverability is handled through explicit memo links or path-discovery output
