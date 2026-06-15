## MODIFIED Requirements

### Requirement: Pro clarification prioritizes topology, communication context choices, and objective semantics
The pro `clarify-intent` and `clarify-execplan` guidance SHALL prioritize questions that affect objective semantics, topology mode, participant communication, predecessor-context choices, loop process, termination, state, workspace, and validation.

The pro clarification guidance SHALL show high-level ASCII/text diagrams for agent architecture and loop structure in TUI chat output before the first intent clarification question when enough source material exists.

The pro clarification guidance SHALL NOT emit fenced `mermaid` blocks in chat visual summaries for `clarify-intent`, `clarify-execplan`, or the routed `clarify` alias path.

This chat-output rule SHALL NOT remove or weaken generated execplan artifact requirements that require Mermaid diagrams in generated Markdown files.

The pro clarification guidance SHALL avoid low-impact wording or file-organization questions while topology mode, communication context needs, loop process, objective, or termination remains unclear.

#### Scenario: Clarification asks topology-mode question early
- **WHEN** intention source can plausibly mean either pairwise-tree or generic-graph execution
- **THEN** pro clarification asks about topology mode before asking low-impact local file questions
- **AND THEN** accepted answers are recorded in intention material or ADRs according to the operation

#### Scenario: Clarification visualizes loop shape
- **WHEN** intention source identifies participants or route candidates
- **THEN** pro clarification shows a high-level ASCII/text architecture or loop-structure diagram in chat
- **AND THEN** unknown topology or context details are marked as unknown rather than invented

#### Scenario: Execplan clarification summarizes generated diagrams for chat
- **WHEN** `clarify-execplan` reports process or topology context from generated artifacts that contain Mermaid diagrams
- **THEN** pro clarification summarizes the relevant shape as ASCII/text in chat instead of pasting a fenced `mermaid` block
- **AND THEN** the generated artifact remains governed by the generated execplan artifact contract

#### Scenario: Generated artifacts retain Mermaid contracts
- **WHEN** pro generation or validation handles generated execplan process or topology artifacts
- **THEN** Mermaid requirements for those generated Markdown artifacts remain in force
- **AND THEN** the chat visual-summary rule does not require converting generated artifacts to ASCII
