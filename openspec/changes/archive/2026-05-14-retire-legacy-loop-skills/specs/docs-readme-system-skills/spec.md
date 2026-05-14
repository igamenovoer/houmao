## ADDED Requirements

### Requirement: README system-skills narrative lists pro as the loop skill
The README system-skills sections SHALL list `houmao-agent-loop-pro` as the current packaged loop skill.

The README SHALL NOT list retired pairwise or generic loop packages as current installed loop skills.

#### Scenario: Reader sees current loop inventory in README
- **WHEN** a reader inspects README system-skill inventory or auto-install prose
- **THEN** the loop entry names `houmao-agent-loop-pro`
- **AND THEN** the prose does not claim that retired loop packages are current auto-installed skills
