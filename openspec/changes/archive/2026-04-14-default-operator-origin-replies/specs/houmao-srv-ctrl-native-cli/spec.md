## ADDED Requirements

### Requirement: `houmao-mgr agents mail post` defaults to operator mailbox replies
`houmao-mgr agents mail post` SHALL default omitted `--reply-policy` input to `operator_mailbox`.

The command SHALL continue to accept explicit `--reply-policy none` and explicit `--reply-policy operator_mailbox`.

When `--reply-policy none` is supplied, the created operator-origin message SHALL remain no-reply and later replies against that message SHALL fail explicitly.

When `--reply-policy` is omitted or supplied as `operator_mailbox`, the created operator-origin message SHALL allow replies back to the reserved operator mailbox `HOUMAO-operator@houmao.localhost`.

The command help SHALL report the reply-policy default as `operator_mailbox`.

#### Scenario: Omitted CLI reply policy creates a reply-enabled operator-origin post
- **WHEN** an operator runs `houmao-mgr agents mail post --agent-name alice --subject "..." --body-content "..."` without `--reply-policy`
- **THEN** `houmao-mgr` dispatches the post with reply policy `operator_mailbox`
- **AND THEN** the resulting operator-origin message accepts replies to `HOUMAO-operator@houmao.localhost`

#### Scenario: Explicit CLI no-reply policy remains supported
- **WHEN** an operator runs `houmao-mgr agents mail post --agent-name alice --subject "..." --body-content "..." --reply-policy none`
- **THEN** `houmao-mgr` dispatches the post with reply policy `none`
- **AND THEN** a later reply against that operator-origin message is rejected explicitly

#### Scenario: CLI help reflects the new default
- **WHEN** an operator reads help for `houmao-mgr agents mail post`
- **THEN** the `--reply-policy` option reports `operator_mailbox` as the default
- **AND THEN** it still lists `none` as the no-reply opt-out value
