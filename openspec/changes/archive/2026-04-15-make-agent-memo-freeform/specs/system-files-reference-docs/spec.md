## ADDED Requirements

### Requirement: System-files reference documents memo and page ownership
System-files reference documentation SHALL identify `houmao-memo.md` as user/LLM-owned free-form Markdown.

The reference SHALL identify `pages/` as a contained page directory whose files may be linked from the memo by authored Markdown links.

The reference SHALL state that Houmao owns path resolution and containment, not memo content generation.

#### Scenario: Reference reader sees the ownership boundary
- **WHEN** a reader opens the system-files managed memory reference
- **THEN** the reference states that Houmao owns the memory root and page containment
- **AND THEN** the reference states that users and LLMs own the memo content

### Requirement: System-files reference omits generated index and migration behavior
System-files reference documentation SHALL NOT describe a generated memo page index, memo reindex operation, or migration behavior for old generated marker blocks.

#### Scenario: Reference reader does not see migration guidance
- **WHEN** a reader opens the system-files managed memory reference
- **THEN** the reference does not instruct them to migrate old generated page-index blocks
- **AND THEN** the reference treats existing memo content as ordinary Markdown
