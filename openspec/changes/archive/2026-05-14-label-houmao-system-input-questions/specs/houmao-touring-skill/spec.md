## ADDED Requirements

### Requirement: Touring system-input questions label required and optional values
When `houmao-touring` asks the user for Houmao system setup or lifecycle input, it SHALL identify required values separately from optional values or skip paths.

The touring question SHALL keep first-time-user guidance, including plain-language concept names, short explanations, realistic examples, and recommended defaults where useful.

This requirement SHALL apply to project overlay setup, mailbox setup, specialist or profile setup, managed-agent launch, post-launch gateway or mailbox setup, lifecycle follow-up, and cleanup choices.

This requirement SHALL NOT apply to questions about the user's task content or domain goals unless the question is specifically about Houmao runtime behavior.

#### Scenario: Project setup question labels required and optional values
- **WHEN** the guided tour asks the user to create or select a Houmao project overlay
- **THEN** the question labels the required project location or confirmation separately from optional naming, discovery-mode, or skip choices
- **AND THEN** it still explains why the project overlay matters

#### Scenario: Optional branch shows skip path as optional
- **WHEN** the guided tour offers an optional mailbox, profile, gateway, or post-launch branch
- **THEN** the question labels the branch-specific blocking values as required only if the user chooses that branch
- **AND THEN** it labels the skip path or default as optional

#### Scenario: Lifecycle choice explains terms and labels inputs
- **WHEN** the guided tour asks whether to stop, relaunch, clean up, or inspect a managed agent
- **THEN** it explains the difference between the lifecycle choices
- **AND THEN** it labels the required target selector and selected lifecycle action separately from optional modifiers
