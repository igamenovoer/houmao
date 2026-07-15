## ADDED Requirements

### Requirement: Easy-specialist guide documents current Codex and Kimi reasoning ladders
The easy-specialist guide SHALL document the maintained GPT-5.6 Sol, Terra, and Luna reasoning-level mappings, including `ultra` only for models whose Codex catalog advertises it. The guide SHALL explain that Kimi reasoning levels follow the selected alias's declared ordered efforts and fail clearly when no maintained effort ladder is available.

#### Scenario: Reader can select GPT-5.6 ultra intentionally
- **WHEN** a reader wants a GPT-5.6 Sol or Terra specialist at `ultra`
- **THEN** the guide identifies reasoning level `6`
- **AND THEN** it does not claim Luna supports `ultra`

#### Scenario: Reader understands Kimi effort discovery
- **WHEN** a reader configures a Kimi specialist with a reasoning level
- **THEN** the guide explains that the selected model alias must declare an ordered effort ladder
- **AND THEN** it does not present a universal Kimi effort table

