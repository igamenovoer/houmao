# runtime-tmux-control-input Specification

## Purpose
Define parsing and delivery rules for tmux-backed runtime control-input sequences.

## Requirements
### Requirement: Mixed control-input sequences use exact tmux-key tokens
The system SHALL accept a control-input sequence string composed of literal text segments and special-key tokens written as exact `<[key-name]>` substrings.

The parser SHALL:
- treat `key-name` as case-sensitive,
- recognize a special-key token only when the substring uses the exact `<[key-name]>` form with no internal whitespace, and
- preserve non-matching substrings as literal text.

The implementation SHALL guarantee support for at least these exact key names: `Enter`, `Escape`, `Up`, `Down`, `Left`, `Right`, `Tab`, `BSpace`, `C-c`, `C-d`, and `C-z`.

#### Scenario: Sequence mixes literal text and exact special keys
- **WHEN** a caller provides the sequence `"/model<[Enter]><[Down]><[Enter]>"`
- **THEN** the system parses the sequence as ordered segments of literal text `"/model"`, special key `Enter`, special key `Down`, and special key `Enter`
- **AND THEN** delivery preserves that same left-to-right order

#### Scenario: Whitespace inside token markers prevents special-key recognition
- **WHEN** a caller provides the sequence `"literal <[ Escape ]> text"`
- **THEN** the system does not recognize `<[ Escape ]>` as a special-key token
- **AND THEN** it treats that substring as literal text

#### Scenario: Stray `<[` remains literal while a later exact token is recognized
- **WHEN** a caller provides the sequence `"<[<[Enter]>"`
- **THEN** the system preserves the leading `"<["` as literal text
- **AND THEN** it recognizes the later exact token `<[Enter]>` as an `Enter` keypress

### Requirement: Escape mode disables special-key parsing for the entire sequence
The system SHALL provide a mode that disables special-key parsing for the provided control-input sequence and sends the entire string literally.

#### Scenario: Escape mode keeps token-like substrings literal
- **WHEN** a caller enables escape mode and provides the sequence `"/model<[Enter]>"`
- **THEN** the system sends the exact literal characters `/model<[Enter]>`
- **AND THEN** it does not synthesize a special-key event for `Enter`

### Requirement: Raw control-input delivery preserves stream semantics
The system SHALL deliver parsed literal text and special-key tokens to the live tmux target in order, SHALL NOT append an implicit `Enter` at the end of the provided sequence, and SHALL require an explicit `<[Enter]>` token when submit behavior is desired.

The implementation SHALL deliver literal text segments using tmux literal-text mode (`send-keys -l`) and SHALL deliver special-key tokens using tmux key-name delivery (`send-keys` without literal mode).

Literal text segments SHALL support normal punctuation and other literal special characters without requiring the high-level prompt-submission path.

#### Scenario: Plain text does not auto-submit
- **WHEN** a caller provides the sequence `"/model"`
- **THEN** the system delivers the literal text `/model` to the live terminal
- **AND THEN** it does not append `Enter` automatically

#### Scenario: Explicit Enter token triggers submit behavior
- **WHEN** a caller provides the sequence `"/model<[Enter]>"`
- **THEN** the system delivers the literal text `/model`
- **AND THEN** it delivers an `Enter` keypress only because the caller included `<[Enter]>` explicitly

#### Scenario: Guaranteed minimum control keys are accepted
- **WHEN** a caller provides the sequence `"<[Escape]><[C-c]>"`
- **THEN** the system accepts both exact tokens as supported special keys
- **AND THEN** it delivers those keypresses in order without appending `Enter`

### Requirement: Unsupported exact key tokens fail explicitly
When a substring uses the exact `<[key-name]>` token form but `key-name` is not supported by the implementation's tmux key handling, the operation SHALL fail with an explicit error that identifies the offending token.

The implementation MAY support additional tmux key names beyond the guaranteed minimum set, but tokens outside the implementation-supported set SHALL still fail explicitly.

#### Scenario: Unsupported exact token is rejected
- **WHEN** a caller provides the sequence `"<[escape]>"`
- **THEN** the system rejects the request because `escape` does not match a supported case-sensitive tmux key name
- **AND THEN** the error identifies `"<[escape]>"` as the invalid token
