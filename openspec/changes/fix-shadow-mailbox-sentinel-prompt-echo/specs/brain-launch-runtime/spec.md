## MODIFIED Requirements

### Requirement: Runtime mail commands use skill-directed prompts with appended mailbox metadata and validate a sentinel-delimited result contract
The runtime SHALL translate each `mail` command invocation into a runtime-owned mailbox prompt delivered through the existing prompt-turn control path rather than directly manipulating mailbox files or mailbox SQLite state itself.

That mailbox prompt SHALL explicitly tell the agent which projected mailbox system skill to use for the mailbox operation and SHALL append structured mailbox metadata needed for the mailbox operation and result parsing.

The `mail` command handler SHALL validate exactly one structured mailbox result payload returned between `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` sentinels in the agent output and SHALL surface that result to the operator in a parseable form.

That sentinel-delimited structured result contract SHALL be the correctness boundary for mailbox result parsing. The runtime SHALL NOT rely on generic shadow dialog projection fidelity as the guarantee that mailbox result text was recovered exactly.

For `shadow_only` mailbox commands, the runtime SHALL continue polling post-submit shadow text for the active request after generic lifecycle completion becomes provisionally satisfied until exactly one sentinel-delimited mailbox result payload for that request is visible or an existing timeout, stall, blocked-surface, unsupported-surface, or disconnect failure ends the command.

For `shadow_only` mailbox commands, a submit-ready surface without a complete sentinel-delimited mailbox result for the active request SHALL be treated as provisional only. The runtime SHALL NOT return mailbox success or a missing-sentinel parse failure solely because the generic shadow lifecycle gate became satisfied before the sentinel contract was observed.

For `shadow_only` mailbox commands, prompt-echo mentions of `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` inside ordinary prose, echoed mailbox request content, or echoed response-contract metadata SHALL NOT satisfy mailbox completion gating or mailbox result validation by themselves.

For `shadow_only` mailbox commands, mailbox completion gating and mailbox result validation SHALL use the same active-request result-selection contract so that surfaces ignored as prompt-echo noise during provisional completion are not later treated as malformed mailbox results.

#### Scenario: Mail command uses skill-directed prompt with appended mailbox metadata
- **WHEN** a developer invokes a runtime `mail` command for a mailbox-enabled session
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the projected mailbox system skill the agent should use
- **AND THEN** that prompt tells the agent to inspect the shared mailbox `rules/` directory before interacting with shared mailbox state
- **AND THEN** that prompt tells the agent to use shared scripts from `rules/scripts/` for any mailbox step that touches `index.sqlite` or `locks/`
- **AND THEN** that prompt appends structured mailbox metadata for the mailbox operation and result contract

#### Scenario: Mail command returns structured mailbox result
- **WHEN** a mailbox-enabled agent completes a runtime `mail` request
- **THEN** the agent returns one structured mailbox result payload describing the mailbox operation outcome between the required sentinels
- **AND THEN** the runtime validates and prints that result in a parseable form for the operator

#### Scenario: Shadow-mode mailbox parsing relies on the schema contract rather than exact projection cleanup
- **WHEN** a mailbox-enabled shadow-mode session returns one sentinel-delimited JSON result together with surrounding TUI noise or imperfect projection cleanup
- **THEN** the runtime still treats the sentinel-delimited structured payload as the reliability boundary
- **AND THEN** mailbox correctness does not depend on `dialog_projection.dialog_text` being an exact recovered reply transcript

#### Scenario: Shadow-mode mailbox waits past transient submit-ready rebound for sentinel result
- **WHEN** a mailbox-enabled `shadow_only` session returns to a submit-ready surface before the sentinel-delimited mailbox result for the active request is visible
- **THEN** the runtime keeps polling post-submit shadow text instead of returning mailbox success or a missing-sentinel parse failure
- **AND THEN** the runtime surfaces the mailbox result only after exactly one sentinel-delimited payload for that request is observed or the existing bounded turn failure policy fires

#### Scenario: Shadow-mode mailbox ignores echoed request sentinel names
- **WHEN** a mailbox-enabled `shadow_only` session echoes the runtime-owned mailbox prompt or response-contract metadata so that the sentinel names appear in projected text before any real mailbox result block is emitted
- **THEN** the runtime treats those echoed sentinel mentions as provisional noise rather than mailbox-result evidence
- **AND THEN** the runtime keeps polling until a real active-request mailbox result payload is observed or the existing bounded turn failure policy fires

#### Scenario: Mail command fails on malformed sentinel payload
- **WHEN** a mailbox-enabled agent omits the required sentinels, emits malformed JSON inside a real sentinel-delimited result block, or returns more than one sentinel-delimited mailbox result payload for the active request
- **THEN** the runtime returns an explicit mailbox-result parsing error for that `mail` command
- **AND THEN** the runtime does not send an automatic retry prompt in v1

#### Scenario: Mail command fails fast when session cannot accept a new turn
- **WHEN** a developer invokes a runtime `mail` command for a session that is already busy or otherwise cannot safely accept a new prompt turn
- **THEN** the runtime returns an explicit mailbox-command error
- **AND THEN** the runtime does not silently queue hidden mailbox work for later execution
