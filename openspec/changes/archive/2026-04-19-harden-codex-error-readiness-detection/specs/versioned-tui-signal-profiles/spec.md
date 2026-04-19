## ADDED Requirements

### Requirement: Drift-prone failure and retry matching uses bounded semantic patterns
For drift-prone prompt, status, error, warning, or retry surfaces, a selected versioned TUI profile SHALL match current-turn signal families through bounded structural scope plus essential semantic tokens rather than through exact full-sentence literals alone.

Those bounded semantic patterns SHALL remain profile-private implementation details of the selected profile.

The selected profile SHALL scope those patterns to the visual role that the signal plays on the current surface, such as prompt-adjacent terminal failure blocks or live-edge retry status, rather than applying the same matcher to arbitrary historical transcript text.

The shared tracker engine SHALL continue to consume only normalized outputs from the selected profile rather than exact matched text fragments.

#### Scenario: Wording drift within the same failure family still matches
- **WHEN** a supported TUI version changes the wording of a current bounded failure or retry surface while preserving the same essential semantic tokens and visual role
- **THEN** the selected profile can continue to match that current signal family without requiring the previous exact full-sentence literal
- **AND THEN** the shared tracker engine does not require a separate rewrite to absorb that wording drift

#### Scenario: Missing essential semantics do not create a false match
- **WHEN** visible text shares some incidental words with a known failure or retry family but does not carry the essential semantic tokens for that family inside the bounded current-turn region
- **THEN** the selected profile does not classify that surface as that failure or retry family
- **AND THEN** the shared tracker engine does not receive a manufactured stronger lifecycle conclusion from partial word overlap

#### Scenario: Historical text outside the bounded current-turn region does not reuse the same semantic matcher
- **WHEN** a supported TUI transcript still shows older warning, error, or retry text outside the bounded current-turn region
- **THEN** the selected profile does not apply the current-turn semantic matcher to that historical text alone
- **AND THEN** the shared tracker engine can decide the current turn from the bounded present-tense surface instead of from stale transcript wording
