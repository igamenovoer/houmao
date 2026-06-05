## ADDED Requirements

### Requirement: Claude prompt behavior distinguishes ghost suggestions by style rather than text

For Claude Code profiles that support prompt-payload style analysis, the selected profile SHALL distinguish prompt-line ghost suggestion payloads from user-authored draft input using raw rendering and style evidence from the current prompt region rather than exact suggestion text.

A Claude prompt payload SHALL be eligible for ghost-suggestion classification only when the profile recognizes the payload's non-space characters as rendered wholly in a suggestion style that is visually distinct from ordinary typed prompt text, such as a profile-owned darker or lower-contrast foreground style.

The selected profile SHALL classify such a pure ghost-suggestion payload as placeholder or suggestion content rather than draft input.

The selected profile SHALL classify any prompt payload containing ordinary typed-payload style as draft input, including mixed prompt lines where an operator-typed prefix is followed by a styled suggestion suffix.

The selected profile SHALL remain conservative for unrecognized prompt styling and SHALL NOT classify a non-empty prompt payload as a ghost suggestion solely because the payload text matches a known suggestion phrase.

#### Scenario: Darker arbitrary suggestion text is placeholder content

- **WHEN** the Claude Code prompt line shows a non-empty payload rendered wholly in the profile-recognized darker ghost-suggestion style
- **AND WHEN** the payload text is arbitrary suggestion text rather than a fixed literal
- **THEN** the selected Claude profile classifies the prompt payload as placeholder or suggestion content
- **AND THEN** it does not expose that payload as user-authored draft text

#### Scenario: Changed suggestion wording still classifies from style

- **WHEN** Claude Code changes the visible auto-suggestion wording while preserving the same profile-recognized ghost-suggestion rendering style
- **THEN** the selected Claude profile continues to classify the prompt payload from style evidence
- **AND THEN** it does not require a literal match for the old suggestion text

#### Scenario: Mixed typed prefix and suggestion suffix remains a draft

- **WHEN** the Claude Code prompt line contains an ordinary typed-payload span and a darker styled suggestion span
- **THEN** the selected Claude profile classifies the prompt payload as draft input
- **AND THEN** the shared tracker can preserve the safety rule that user-authored draft input blocks prompt injection

#### Scenario: Unrecognized styled payload degrades conservatively

- **WHEN** the Claude Code prompt line contains non-empty payload text with styling that is neither ordinary typed-payload style nor a profile-recognized ghost-suggestion style
- **THEN** the selected Claude profile does not classify that payload as a ghost suggestion
- **AND THEN** it may report an unknown prompt presentation rather than manufacturing prompt readiness
