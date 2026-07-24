## ADDED Requirements

### Requirement: Supported TUI profiles derive provider-native pending-input signals

The selected Codex TUI, Claude Code, and Kimi Code profiles SHALL derive a normalized `pending_input` tristate from raw captured snapshot text and profile-owned structural or rendering evidence.

Each profile SHALL scope pending-input evidence to the current live queue/composer surface so historical transcript text does not create a positive result. The profile SHALL emit `unknown` rather than `no` when required structural bounds are missing or ambiguous.

The normalized signal SHALL describe presence only. Provider-specific pending counts MAY remain diagnostic or qualification metadata and SHALL NOT be required in the shared public state.

#### Scenario: Codex queued-follow-up evidence becomes a normalized pending signal

- **WHEN** the selected Codex profile recognizes its bounded current queued-follow-up or pending-input structure
- **THEN** it emits `pending_input=yes`
- **AND THEN** the shared reducer does not need to recover that fact from a provider-specific active reason

#### Scenario: Kimi queue-visible evidence becomes a normalized pending signal

- **WHEN** the selected Kimi profile recognizes its current queue-visible or queued-message structure
- **THEN** it emits `pending_input=yes`
- **AND THEN** stale Kimi transcript prose does not create the same signal

#### Scenario: Complete provider surface without a queue emits no

- **WHEN** a selected supported profile can locate a complete current queue/composer surface and finds no submitted pending instruction
- **THEN** it emits `pending_input=no`
- **AND THEN** it does not require the current turn to be ready before making that negative queue decision

#### Scenario: Multi-prompt queue remains a binary positive

- **WHEN** a selected provider profile observes one, two, or three submitted prompts in the provider-native pending surface
- **THEN** it emits `pending_input=yes` for each supported count
- **AND THEN** the public signal does not vary with provider-specific queue depth

### Requirement: Claude pending-input detection uses bounded structure and rendering semantics rather than suggestion literals

For supported Claude Code profiles, pending-input detection SHALL locate the bottom current composer and its framing separators, classify composer payload through the profile-owned empty/draft/ghost-suggestion behavior, and inspect the bounded region immediately above that composer.

The Claude profile SHALL report `pending_input=yes` only when that bounded region contains a non-empty indented Claude user-input cell in the queued-preview position and no assistant response, tool block, or current activity cell intervenes between the candidate queued cell and the current composer frame.

Prompt-area suggestion text SHALL NOT be sufficient positive or negative pending-input evidence. The detector SHALL NOT require an exact phrase such as an instruction for editing queued messages. Ghost suggestions SHALL continue to be interpreted from profile-owned rendering or style evidence.

When the composer frame, queued-preview boundary, or relevant rendering semantics are incomplete or unrecognized, the Claude profile SHALL emit `pending_input=unknown` rather than a confident negative result.

#### Scenario: Changed or localized suggestion wording does not change a structural positive

- **WHEN** a Claude surface contains a structurally valid queued-preview user cell above the framed composer
- **AND WHEN** the ghost suggestion uses arbitrary, changed, or localized wording in a recognized suggestion style
- **THEN** the selected Claude profile emits `pending_input=yes`
- **AND THEN** it does not compare the suggestion payload with a fixed string

#### Scenario: Queued row remains positive when suggestion text is absent

- **WHEN** a Claude surface contains a structurally valid queued-preview user cell above an otherwise empty framed composer
- **THEN** the selected Claude profile emits `pending_input=yes`
- **AND THEN** the absence of queue-editing suggestion text does not suppress the positive result

#### Scenario: Ghost suggestion alone is not a queue

- **WHEN** the bottom Claude composer contains a recognized ghost suggestion but no queued-preview user cell exists above its frame
- **THEN** the selected Claude profile does not emit `pending_input=yes`
- **AND THEN** a complete negative surface emits `pending_input=no`

#### Scenario: Historical queue-like prose is not a queue

- **WHEN** Claude transcript history contains queue-related words or an older user-input cell separated from the current composer by assistant output, tool output, or current activity
- **THEN** the selected Claude profile does not use that historical content as pending-input evidence
- **AND THEN** it derives the result only from the bounded current queue/composer structure

#### Scenario: Cropped Claude structure is unknown

- **WHEN** a wrapped, resized, or cropped Claude snapshot does not preserve enough of the queued-preview and composer framing structure to decide safely
- **THEN** the selected Claude profile emits `pending_input=unknown`
- **AND THEN** it does not convert missing structure into `pending_input=no`
