## ADDED Requirements

### Requirement: Local-interactive runtime separates semantic prompt submission from raw control input

For tmux-backed `local_interactive` sessions, the runtime SHALL expose a semantic prompt-submission operation that is distinct from the raw control-input operation.

The semantic prompt-submission operation SHALL mean “submit this message as one provider turn.” The raw control-input operation SHALL mean “inject these literal characters and exact special-key tokens into the live TUI.”

The raw control-input operation SHALL continue using the exact `<[key-name]>` contract defined by the runtime tmux-control-input capability, including explicit Enter-only submission behavior and optional literal escape mode for the entire sequence.

The semantic prompt-submission operation SHALL treat the entire prompt body as literal text, SHALL NOT interpret `<[key-name]>` substrings as special keys, and SHALL automatically submit once at the end.

#### Scenario: Semantic prompt submission is not routed through raw send-keys

- **WHEN** the runtime submits a prompt to a live `local_interactive` session
- **THEN** it uses the semantic prompt-submission path rather than the raw `<[key-name]>` control-input path
- **AND THEN** runtime-owned prompt semantics remain distinct from generic TUI key injection

#### Scenario: Prompt-looking special-key tokens remain literal under send-prompt

- **WHEN** the runtime semantically submits the prompt body `reply with <[Enter]> literally`
- **THEN** the provider receives the literal text `reply with <[Enter]> literally`
- **AND THEN** the runtime does not interpret that substring as a special key before the automatic final submit

#### Scenario: Raw control input preserves the exact special-key contract

- **WHEN** the runtime sends the raw control-input sequence `"/model<[Enter]><[Down]>"` to a live `local_interactive` session
- **THEN** it preserves the exact `<[key-name]>` parsing and delivery behavior defined for tmux control input
- **AND THEN** that raw path does not gain implicit prompt-submission semantics beyond the explicit keys the caller provided

### Requirement: Local-interactive semantic prompt submission uses submit-aware tmux delivery

For tmux-backed `local_interactive` sessions, semantic prompt submission SHALL use a submit-aware tmux delivery strategy that pastes the prompt text and submits it as separate phases.

At minimum, that strategy SHALL:

- insert the prompt text through tmux paste-buffer delivery rather than only through rapid literal `send-keys -l`
- request bracketed-paste wrappers when the target application supports them
- send the submit action separately from text insertion

For provider TUIs that distinguish explicit paste input from fast typed-character bursts, the runtime SHALL treat successful semantic prompt submission as requiring an actual submitted provider turn rather than leaving the prompt staged as multiline draft text in the composer.

#### Scenario: Codex prompt submission becomes a real submitted turn

- **WHEN** the runtime semantically submits a prompt into a live Codex `local_interactive` session
- **THEN** the provider receives that prompt as a submitted turn
- **AND THEN** the prompt is not left behind merely as multiline draft text caused by paste-burst reinterpretation of the submit key

#### Scenario: Submit-aware prompt delivery keeps raw key behavior separate

- **WHEN** the runtime semantically submits a prompt into a live `local_interactive` session
- **THEN** the runtime performs text insertion and submit as separate phases
- **AND THEN** later raw control-input delivery continues to behave according to the exact keys the caller requested rather than inheriting semantic prompt-submission side effects

#### Scenario: Raw send-keys does not auto-submit without explicit Enter

- **WHEN** the runtime sends the raw control-input sequence `"hello world"` to a live `local_interactive` session
- **THEN** it inserts the literal text `hello world`
- **AND THEN** it does not submit the draft because the caller did not include an explicit `<[Enter]>`
