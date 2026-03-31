## ADDED Requirements

### Requirement: Runtime-owned mailbox skill projection separates gateway operations from transport-specific guidance and uses Houmao-owned skill naming
The system SHALL project a common runtime-owned mailbox skill for shared gateway mailbox operations into every mailbox-enabled session in addition to the active transport-specific mailbox skill.

Projected Houmao-owned mailbox skills SHALL use a `houmao-<skillname>` naming convention under the visible mailbox subtree so runtime-owned Houmao skills are distinguishable from role-authored or third-party skill names.

That `houmao-<skillname>` convention SHALL also define the activation boundary for Houmao-owned skills: the instruction text must include the keyword `houmao` when it intends to trigger a Houmao-owned skill.

That common skill SHALL live under the visible mailbox subtree alongside transport skills and SHALL be available at `skills/mailbox/houmao-email-via-agent-gateway/` for current adapters whose skill destination is `skills`.

The common gateway skill SHALL:
- use `SKILL.md` as a short index rather than a monolithic operation manual,
- publish operation-specific subdocuments for live discovery, check, read, send, reply, and mark-read behavior,
- publish explicit curl-first endpoint references for the shared `/v1/mail/*` surface,
- direct agents to discover the live gateway endpoint through `pixi run houmao-mgr agents mail resolve-live`,
- act as the default installed runtime-owned procedure for attached shared-mailbox work when a live gateway facade is available.

Transport-specific mailbox skills such as `houmao-email-via-filesystem` and `houmao-email-via-stalwart` SHALL remain projected and SHALL narrow their ordinary guidance to transport validation, transport-specific context, and fallback behavior when the gateway facade is unavailable.

#### Scenario: Mailbox-enabled session receives both gateway and transport runtime-owned skills
- **WHEN** the runtime starts a mailbox-enabled session
- **THEN** it projects `skills/mailbox/houmao-email-via-agent-gateway/` into the active skill destination
- **AND THEN** it also projects the runtime-owned mailbox skill for the active transport
- **AND THEN** the agent can discover both skills from the visible mailbox subtree without relying on hidden `.system` entries

#### Scenario: Houmao-owned mailbox skill naming requires explicit `houmao` invocation
- **WHEN** a runtime-owned mailbox skill is intended to be triggered through agent instructions
- **THEN** that skill uses a `houmao-<skillname>` name
- **AND THEN** the instruction text includes the keyword `houmao` when it intends to trigger that Houmao-owned skill
- **AND THEN** ordinary non-Houmao wording does not rely on implicit activation of the Houmao-owned skill

#### Scenario: Gateway mailbox skill uses action subdocuments instead of one packed instruction file
- **WHEN** an agent opens `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md`
- **THEN** that entry document points the agent at action-specific subdocuments for `resolve-live`, `check`, `read`, `send`, `reply`, and `mark-read`
- **AND THEN** it does not pack the full operation guidance only into the top-level `SKILL.md`

#### Scenario: Gateway mailbox skill documents curl-first mailbox operations
- **WHEN** an agent needs to perform ordinary shared mailbox work through the live gateway facade
- **THEN** the runtime-owned gateway skill provides explicit curl examples for `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state`
- **AND THEN** the skill treats those explicit endpoint calls as the ordinary attached-session workflow once `gateway.base_url` is available

#### Scenario: Projected gateway skill is treated as installed operational guidance
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the runtime-owned `houmao-email-via-agent-gateway` skill is already projected into that session
- **AND THEN** notifier and other runtime-owned guidance may instruct the agent to use that installed skill directly for the current mailbox turn

#### Scenario: Transport-specific mailbox skill narrows to transport context and fallback
- **WHEN** an agent opens `skills/mailbox/houmao-email-via-filesystem/SKILL.md` or `skills/mailbox/houmao-email-via-stalwart/SKILL.md`
- **THEN** that transport skill explains transport-specific constraints, references, and no-gateway fallback behavior
- **AND THEN** it points the agent at `skills/mailbox/houmao-email-via-agent-gateway/` for the shared `/v1/mail/*` operation contract instead of duplicating the entire gateway operation tutorial

### Requirement: Runtime-owned mailbox skills use the manager-owned live resolver as the ordinary gateway discovery contract
Projected runtime-owned mailbox skills SHALL direct agents to the manager-owned live resolver `pixi run houmao-mgr agents mail resolve-live` as the ordinary discovery path for the current mailbox binding and any attached gateway facade.

When that resolver returns a `gateway` object, runtime-owned mailbox skills SHALL treat `gateway.base_url` as the exact current endpoint prefix for shared `/v1/mail/*` mailbox operations.

Projected runtime-owned mailbox skills SHALL NOT present `python -m houmao.agents.mailbox_runtime_support resolve-live` as part of the ordinary mailbox operation workflow.

#### Scenario: Gateway mailbox skill obtains the current endpoint from `houmao-mgr agents mail resolve-live`
- **WHEN** an agent follows the runtime-owned gateway mailbox skill for attached shared mailbox work
- **THEN** the skill directs the agent to run `pixi run houmao-mgr agents mail resolve-live`
- **AND THEN** the agent obtains the exact live mailbox endpoint from the returned `gateway.base_url`

#### Scenario: Runtime-owned mailbox skills avoid direct Python-module resolver guidance
- **WHEN** an agent follows the projected mailbox skills for ordinary mailbox work
- **THEN** those skills use `pixi run houmao-mgr agents mail resolve-live` as the supported discovery contract
- **AND THEN** they do not instruct the agent to invoke `python -m houmao.agents.mailbox_runtime_support resolve-live` directly

### Requirement: Joined-session adoption installs Houmao-owned mailbox skills by default
When `houmao-mgr agents join` adopts a mailbox-enabled session, the join workflow SHALL install the Houmao-owned mailbox skill set into the adopted tool home by default so later runtime-owned prompts can rely on those skills being installed.

That joined-session installation SHALL:
- resolve the adopted tool home through the join workflow’s authoritative home-resolution path,
- project Houmao-owned mailbox skills only under reserved `houmao-<skillname>` paths in the adapter’s skill destination,
- preserve unrelated user-authored skill directories,
- fail explicitly when default installation is required but the target skill destination cannot be resolved or updated safely.

The join workflow MAY expose an explicit operator opt-out for Houmao-owned mailbox skill installation. When that opt-out is used, later runtime-owned mailbox prompts and docs SHALL NOT assume those skills are installed for that joined session.

#### Scenario: Joined mailbox-enabled session receives Houmao-owned mailbox skills by default
- **WHEN** an operator uses `houmao-mgr agents join` to adopt a mailbox-enabled session without opting out of Houmao skill installation
- **THEN** the join workflow projects the Houmao-owned mailbox skills into the adopted tool home under the adapter’s skill destination
- **AND THEN** later runtime-owned mailbox and gateway prompts may rely on those installed skill paths for that joined session

#### Scenario: Join preserves unrelated user-authored skills
- **WHEN** `houmao-mgr agents join` installs Houmao-owned mailbox skills into an adopted tool home
- **THEN** it writes only to reserved Houmao-owned mailbox skill paths
- **AND THEN** it does not delete or overwrite unrelated user-authored non-Houmao skill directories in that same skill destination

#### Scenario: Join fails closed when required Houmao-owned skill installation cannot complete
- **WHEN** `houmao-mgr agents join` is using default Houmao mailbox skill installation
- **AND WHEN** the adopted tool home or skill destination cannot be resolved or updated safely
- **THEN** the join command fails explicitly
- **AND THEN** it does not publish a managed session whose later runtime prompts would assume missing Houmao-owned mailbox skills

#### Scenario: Explicit join opt-out disables the installed-skill assumption
- **WHEN** an operator uses the explicit opt-out for Houmao mailbox skill installation during `houmao-mgr agents join`
- **THEN** the join workflow may continue without projecting those Houmao-owned mailbox skills
- **AND THEN** later runtime-owned mailbox prompts for that joined session do not assume the Houmao-owned mailbox skills are installed
