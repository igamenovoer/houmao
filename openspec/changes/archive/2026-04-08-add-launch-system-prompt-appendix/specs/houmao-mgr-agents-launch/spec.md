## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports one-shot launch-owned system-prompt appendix
`houmao-mgr agents launch` SHALL accept optional launch-owned system-prompt appendix input through:

- `--append-system-prompt-text`
- `--append-system-prompt-file`

Those options SHALL be mutually exclusive.

When either option is supplied, the provided appendix SHALL participate only in the current launch's effective prompt composition and SHALL NOT rewrite the source role prompt or any stored launch profile.

When the launch also resolves a launch-profile prompt overlay, the appendix SHALL be appended after overlay resolution within the current launch's effective prompt composition.

#### Scenario: Direct managed launch appends one-shot prompt text for the current launch only
- **WHEN** an operator runs `houmao-mgr agents launch --agents researcher --provider codex --append-system-prompt-text "Prefer the current branch naming rules."`
- **THEN** the current launch's effective prompt includes a launch appendix after the other resolved prompt-body sections
- **AND THEN** a later launch without the appendix option does not inherit that one-shot appendix

#### Scenario: Profile-backed launch appends file-based appendix after overlay resolution
- **WHEN** launch profile `alice` already contributes a prompt overlay
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --append-system-prompt-file /tmp/appendix.md`
- **THEN** the current launch appends the file content after the resolved launch-profile overlay
- **AND THEN** stored launch profile `alice` remains unchanged

#### Scenario: Launch rejects conflicting appendix inputs
- **WHEN** an operator supplies both `--append-system-prompt-text` and `--append-system-prompt-file` on the same `houmao-mgr agents launch` invocation
- **THEN** the command fails clearly before brain construction begins
- **AND THEN** it does not start a managed session for that invalid launch request
