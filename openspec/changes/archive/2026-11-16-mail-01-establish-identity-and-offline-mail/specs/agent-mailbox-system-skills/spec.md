# Spec Delta

## MODIFIED Requirements

### Requirement: Mailbox system skills use a stable resolver contract for current mailbox discovery
Projected mailbox skills SHALL discover current mail state through the scoped `houmao-mgr agents self mail resolve-live` or explicitly targeted `agents single` equivalent. The result SHALL expose both optional bindings, owner/channel/binding scope, revisions, canonical mail identity, safe operational information, and the current validated gateway endpoint. It SHALL not depend on inherited mailbox environment snapshots or expose credential material.

#### Scenario: Filesystem mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** an agent resolves its configured offline mail
- **THEN** it receives the current offline binding and selected registry context
- **AND THEN** it can use the supported facade without scraping tmux environment or raw manifests

#### Scenario: Stalwart mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** an agent resolves its configured Stalwart online mail
- **THEN** it receives the online provider identity and current binding revision alongside any offline binding
- **AND THEN** ordinary mailbox work does not require receiving a password or credential-file path

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, projected mailbox system skills SHALL resolve current mailbox bindings through the runtime-owned live resolver exposed by `houmao-mgr agents self mail resolve-live` rather than relying on the provider process's inherited mailbox env snapshot, mailbox-specific tmux env, or a direct Python-module entrypoint.

That live resolver SHALL:

- support same-session discovery when selectors are omitted inside the owning managed tmux session,
- use `HOUMAO_MANIFEST_PATH` as the primary current-session discovery source with `HOUMAO_AGENT_ID` as fallback,
- derive current mailbox state from the durable session mailbox binding instead of from targeted mailbox tmux env keys,
- surface safe current information for both optional bindings, their scopes and revisions, without credential material,
- surface the current validated gateway mail-facade binding for the session when a live gateway is attached,
- avoid requiring the agent to parse raw manifest JSON or enumerate unrelated tmux env vars manually.

When a live gateway is attached, the resolver SHALL return the exact current `gateway.base_url` needed for attached shared-mailbox work.

#### Scenario: Filesystem mailbox skill observes late-registered binding without provider relaunch
- **WHEN** a tmux-backed filesystem mailbox session receives a mailbox task after late registration updated the durable session mailbox binding
- **THEN** the projected mailbox system skill resolves the current mailbox binding through `houmao-mgr agents self mail resolve-live`
- **AND THEN** the skill observes the refreshed filesystem mailbox state without requiring provider relaunch or mailbox-specific tmux env refresh

#### Scenario: Attached mailbox skill resolves the live gateway mail facade through `houmao-mgr agents mail`
- **WHEN** a tmux-backed mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** `houmao-mgr agents self mail resolve-live` returns both the current mailbox binding and the validated live gateway mail-facade binding for that same session
- **AND THEN** the projected mailbox system skill can obtain the exact current gateway `base_url` for attached mailbox work without scraping tmux env or guessing a default port

#### Scenario: Stalwart no-gateway mailbox work uses the live resolver instead of stale process env
- **WHEN** a tmux-backed `stalwart` mailbox session performs mailbox work without a live gateway mailbox facade
- **THEN** the projected mailbox system skill resolves the current binding set through `houmao-mgr agents self mail resolve-live`
- **AND THEN** the skill uses the current mailbox binding returned by that manager-owned discovery surface rather than assuming the provider process inherited still-current values at launch

### Requirement: Runtime-owned mailbox skill guidance keeps tmux integration behind the runtime-owned helper boundary
Projected mailbox system skills for tmux-backed sessions SHALL keep raw tmux integration details behind the runtime-owned helper boundary exposed through `houmao-mgr`.

The skill guidance SHALL NOT require the agent to:

- list all tmux session environment variables,
- guess which tmux session to inspect,
- parse raw `show-environment` output structure,
- parse mailbox binding state directly from the session manifest when the runtime-owned helper is available,
- invoke `python -m houmao.agents.mailbox_runtime_support ...` directly as part of ordinary mailbox work.

#### Scenario: Filesystem mailbox skill does not ask the agent to scrape tmux state or call a Python module directly
- **WHEN** a tmux-backed filesystem mailbox session uses the projected mailbox system skill for mailbox work
- **THEN** that skill points the agent at `houmao-mgr agents self mail resolve-live`
- **AND THEN** the skill does not instruct the agent to enumerate unrelated tmux environment state or invoke a direct Python-module resolver entrypoint

### Requirement: Projected mailbox system skills keep routine attached-session actions on the shared gateway facade
When a live loopback gateway exposes the shared `/v1/mail/*` mailbox surface for a mailbox-enabled session, the projected mailbox system skills SHALL treat that shared gateway facade as the default routine action surface for ordinary mailbox work.

Projected mailbox system skills for both filesystem and `stalwart` transports SHALL present that default structurally: resolve current mailbox state through `houmao-mgr agents self mail resolve-live`, use gateway HTTP when it is available, and fall back to `houmao-mgr agents self mail ...` or explicitly targeted `agents single` commands when it is not. Lifecycle actions SHALL retain the selected channel and expected binding; manager lifecycle commands SHALL include `--channel offline|online`.

For this change, ordinary mailbox work includes:

- checking unread mail,
- sending one new message,
- replying to one existing message,
- marking one processed message read.

When projected mailbox skills use the `houmao-mgr agents self mail ...` fallback path, they SHALL preserve the manager command's authority-aware result contract:

- `authoritative: true` means Houmao verified the mailbox outcome through manager-owned or gateway-backed execution,
- `authoritative: false` means Houmao only submitted the mailbox request through a TUI-mediated fallback path and separate verification is required.

When projected mailbox skills expose thin tmux-session-local shell helpers, those helpers SHALL delegate only to gateway HTTP or `houmao-mgr agents self mail ...` rather than to direct Python-module entrypoints or mailbox-owned scripts.

For attached filesystem sessions, projected mailbox system skills SHALL NOT present direct mailbox-owned Python scripts as the ordinary no-gateway fallback path for those routine actions.

For attached `stalwart` sessions, projected mailbox system skills SHALL NOT present direct Python-module mailbox discovery as the ordinary no-gateway fallback path for those routine actions.

#### Scenario: Attached mailbox session uses the shared gateway facade when available
- **WHEN** a mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** the projected mailbox system skill resolves the current gateway endpoint through `houmao-mgr agents self mail resolve-live`
- **AND THEN** the skill directs the agent to use gateway HTTP for the shared mailbox operation instead of reasoning about transport details directly

#### Scenario: Mailbox session without gateway falls back to `houmao-mgr agents mail`
- **WHEN** a mailbox-enabled session has no live shared gateway mailbox facade
- **THEN** the projected mailbox system skill directs the agent to use `houmao-mgr agents self mail ...` for routine mailbox work
- **AND THEN** the fallback remains manager-owned and transport-neutral from the agent's perspective

#### Scenario: Non-authoritative manager fallback result triggers explicit verification
- **WHEN** a projected mailbox system skill uses `houmao-mgr agents self mail send ...` or `reply ...`
- **AND WHEN** that command returns `authoritative: false`
- **THEN** the skill treats the result as submission-only rather than verified mailbox success
- **AND THEN** the skill uses `houmao-mgr agents self mail list`, `status`, or transport-owned mailbox state to verify the requested outcome before assuming the mailbox mutation completed

#### Scenario: Thin shell helpers stay wrappers over supported surfaces
- **WHEN** a projected mailbox skill provides a shell helper for tmux-session-local mailbox work
- **THEN** that helper wraps `houmao-mgr agents self mail resolve-live`, gateway HTTP, or `houmao-mgr agents self mail ...`
- **AND THEN** it does not become a second canonical mailbox contract with independent transport logic

### Requirement: Unified ordinary-mailbox skill uses the manager-owned live resolver as the ordinary gateway discovery contract
Projected runtime-owned mailbox skills SHALL direct agents to the manager-owned live resolver `houmao-mgr agents self mail resolve-live` only when current prompt or context does not already provide the exact current gateway base URL needed for shared `/v1/mail/*` mailbox operations.

When current prompt or context already provides the exact current gateway base URL, runtime-owned mailbox skills SHALL treat that URL as the authoritative endpoint prefix for the current mailbox work and SHALL NOT require redundant manager-based rediscovery.

When the manager-owned live resolver returns a `gateway` object, runtime-owned mailbox skills SHALL treat `gateway.base_url` as the exact current endpoint prefix for channel-selected `/v1/mail/{channel}/...` mailbox operations. The routine SHALL preserve the selected channel and expected binding ID.

Projected runtime-owned mailbox skills SHALL NOT present `pixi run houmao-mgr agents self mail resolve-live` as part of ordinary mailbox operation workflow.

Projected runtime-owned mailbox skills SHALL NOT present `python -m houmao.agents.mailbox_runtime_support resolve-live` as part of the ordinary mailbox operation workflow.

#### Scenario: Unified ordinary-mailbox skill obtains the current endpoint from prompt context when available
- **WHEN** an agent follows the runtime-owned unified ordinary-mailbox skill for shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context already provides the exact current gateway base URL
- **THEN** the skill uses that context-provided base URL as the endpoint prefix for `/v1/mail/*`
- **AND THEN** the agent does not need to rerun manager-based discovery first

#### Scenario: Unified ordinary-mailbox skill falls back to `houmao-mgr agents mail resolve-live`
- **WHEN** an agent follows the runtime-owned unified ordinary-mailbox skill for attached shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context does not provide the exact current gateway base URL
- **THEN** the skill directs the agent to run `houmao-mgr agents self mail resolve-live`
- **AND THEN** the agent obtains the exact live mailbox endpoint from the returned `gateway.base_url`

#### Scenario: Unified ordinary-mailbox skill avoids `pixi` and direct Python-module resolver guidance
- **WHEN** an agent follows the projected mailbox skills for ordinary mailbox work
- **THEN** those skills do not instruct the agent to use `pixi run houmao-mgr agents self mail resolve-live`
- **AND THEN** they do not instruct the agent to invoke `python -m houmao.agents.mailbox_runtime_support resolve-live` directly

## ADDED Requirements

### Requirement: Mailbox skill workflows select channels explicitly
Ordinary and notifier-driven routines SHALL retain the selected channel and expected binding ID through mailbox operations. Canonical online-first identity SHALL not act as transport selection. A notifier round SHALL use its supplied channel, binding ID, and exact gateway endpoint. Binding mismatch SHALL end that round explicitly rather than silently switching to a replacement mailbox.

#### Scenario: Dual-mail agent processes an offline reminder
- **WHEN** the public agent entrypoint routes an offline notification round to its protected mailbox routine
- **THEN** every operation for that round uses the offline channel
- **AND THEN** the online canonical identity does not redirect the round

#### Scenario: Round lacks channel context
- **WHEN** a notifier-driven round has a gateway URL but no selected channel
- **THEN** the routine reports a contract error rather than guessing from the canonical address

### Requirement: Mailbox skill installation is independent of late binding health
Supported runtime prompts SHALL continue using the public agent entrypoint only when its required static routing siblings are installed. Otherwise they SHALL provide maintained API guidance for the selected channel without requiring a body restart, copying skills into project content, or claiming that newly written skill files are already known to a running CLI.

#### Scenario: Already-running mailbox-disabled body gains offline mail
- **WHEN** late registration enables offline mail on a body without an available native mailbox skill route
- **THEN** the notifier supplies the selected channel and direct API workflow
- **AND THEN** it does not require native skill hot-reload to make attachment actionable
