# Spec Delta

## MODIFIED Requirements

### Requirement: Projected mailbox system skills keep routine attached-session actions on the shared gateway facade

When a live gateway exposes the shared `/v1/mail/*` mailbox surface for a mailbox-enabled session, the projected mailbox system skills SHALL use the shared gateway facade for ordinary mailbox work.

Projected mailbox system skills for filesystem and `stalwart` SHALL resolve current mailbox state through `houmao-mgr agents self mail resolve-live` and use a runtime-owned client for live calls. Managed self commands SHALL sign the challenge with the current generation's key. Scoped admins SHALL use an explicit signing key. Skill text, resolver output, and shell examples SHALL omit keys, proof material, and private credential references.

The skills SHALL use the existing separately authorized manager path when the live gateway is absent. An admission refusal or unavailable policy from a protected gateway SHALL end the request. Lifecycle actions SHALL retain the selected channel and expected binding. Manager lifecycle commands SHALL include `--channel offline|online`.

Ordinary mailbox work includes:

- checking unread mail
- sending one new message
- replying to one existing message
- marking one processed message read

When projected mailbox skills use `houmao-mgr agents self mail ...` without a live gateway, they SHALL preserve the manager command's authority-aware result:

- `authoritative: true` means Houmao verified the mailbox outcome through manager-owned or gateway-backed execution
- `authoritative: false` means Houmao submitted the request through a TUI-mediated path and separate verification is required

Thin session-local helpers SHALL delegate to the runtime-owned gateway client or maintained `houmao-mgr` mailbox commands. For attached filesystem and `stalwart` sessions, the routine fallback SHALL be manager-owned and transport-neutral.

#### Scenario: Attached mailbox session uses the shared gateway facade when available

- **WHEN** a mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** the skill resolves the current endpoint through `houmao-mgr agents self mail resolve-live`
- **AND THEN** its runtime-owned client signs the request challenge with the current generation's self key

#### Scenario: Mailbox session without gateway falls back to `houmao-mgr agents mail`

- **WHEN** a mailbox-enabled session has no live shared gateway mailbox facade and the caller has existing manager authority
- **THEN** the skill directs the agent to use `houmao-mgr agents self mail ...` for routine mailbox work
- **AND THEN** the manager uses the established transport-neutral path

#### Scenario: Protected gateway refuses mailbox access

- **WHEN** the runtime-owned client receives an authentication or authorization failure for a protected mailbox operation
- **THEN** it surfaces the refusal as the request outcome
- **AND THEN** neither a local transport nor an admin binding is used as fallback

#### Scenario: Non-authoritative manager fallback result triggers explicit verification

- **WHEN** the manager returns `authoritative: false` for routine send or reply
- **THEN** the skill treats the result as submission-only
- **AND THEN** it verifies the result through supported mailbox state before treating delivery as complete

#### Scenario: Thin shell helpers stay wrappers over supported surfaces

- **WHEN** a projected mailbox skill provides a shell helper for local gateway work
- **THEN** that helper delegates to the runtime-owned client or maintained scoped mailbox commands
- **AND THEN** the same target and credential selection governs the operation
