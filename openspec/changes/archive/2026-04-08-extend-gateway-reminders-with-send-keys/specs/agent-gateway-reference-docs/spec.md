## ADDED Requirements

### Requirement: Gateway reminder reference documentation explains prompt and send-keys delivery
The agent gateway reference documentation SHALL explain gateway reminders as supporting two different delivery kinds:

- semantic `prompt`
- raw `send_keys`

That reminder documentation SHALL explain:

- the purpose of `send_keys` reminders,
- that `send_keys.sequence` uses the exact `<[key-name]>` raw control-input grammar,
- that `send_keys` reminders do not submit reminder `title` or semantic `prompt` text,
- that `send_keys.ensure_enter` defaults to `true`,
- that `ensure_enter=false` is required for exact special-key-only reminders such as `<[Escape]>`,
- that send-keys reminder support is limited by the current gateway backend's raw-control capability,
- that reminders remain direct live gateway HTTP and do not introduce a new `houmao-mgr agents gateway reminders ...` CLI family.

The documentation SHALL present that explanation in a gateway reminder reference page or equivalent gateway-reference entry path that is discoverable from `docs/reference/gateway/index.md`.

#### Scenario: Reader can distinguish prompt reminders from send-keys reminders
- **WHEN** a reader opens the gateway reminder reference documentation
- **THEN** the page explains that reminders may deliver either semantic prompt text or raw control input
- **AND THEN** the page does not present send-keys reminders as ordinary prompt text with special characters in it

#### Scenario: Reader learns ensure-enter default and exact-key opt-out
- **WHEN** a reader opens the gateway reminder reference documentation
- **THEN** the page explains that `ensure_enter` defaults to `true`
- **AND THEN** it also explains that exact special-key reminders such as `<[Escape]>` should set `ensure_enter=false`

#### Scenario: Reader sees backend and CLI boundaries clearly
- **WHEN** a reader opens the gateway reminder reference documentation
- **THEN** the page explains that send-keys reminders depend on backend raw-control support and remain on the direct live `/v1/reminders` surface
- **AND THEN** it does not imply that a new reminder CLI family already exists
