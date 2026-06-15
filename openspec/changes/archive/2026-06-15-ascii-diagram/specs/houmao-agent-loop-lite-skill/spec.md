## ADDED Requirements

### Requirement: Lite clarification uses chat-safe ASCII visuals
The lite `clarify-intent`, `clarify-execplan`, and routed `clarify` alias guidance SHALL use ASCII/text diagrams for any architecture, process, route, implementation-shape, or coverage visual summary shown directly in TUI chat.

Lite clarification chat output SHALL NOT use fenced `mermaid` blocks for those visual summaries.

This rule SHALL apply only to chat summaries and clarification questions. It SHALL NOT add Mermaid requirements, remove optional generated-artifact diagrams, or require generated lite execplan artifacts to be converted to ASCII.

#### Scenario: Intent clarification visualizes source in chat
- **WHEN** lite `clarify-intent` shows participants, routes, phases, or unknowns from intention source
- **THEN** it uses an ASCII/text diagram in chat
- **AND THEN** unknown or unclear parts are marked as unknown rather than invented

#### Scenario: Execplan clarification visualizes implementation shape in chat
- **WHEN** lite `clarify-execplan` summarizes generated Markdown, template, SQLite state, generated skill, or agent-binding shape
- **THEN** it uses ASCII/text in chat rather than a fenced `mermaid` block
- **AND THEN** the summary remains separate from the generated execplan files

#### Scenario: Generated artifacts are outside the chat-only rule
- **WHEN** lite generated execplan artifacts include or omit diagrams according to existing lite generation guidance
- **THEN** lite validation and generation do not change solely because clarification chat diagrams are ASCII/text
- **AND THEN** generated artifacts are not required to replace artifact-level diagrams with ASCII
