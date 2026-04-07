## MODIFIED Requirements

### Requirement: Gemini managed skill projection uses the generic `.agents/skills` root
When Houmao projects Gemini skills into a managed Gemini home or performs default Houmao-owned Gemini skill installation for an adopted session, the system SHALL use `.gemini/skills` as the discoverable Gemini skill root.

#### Scenario: Constructed Gemini home projects selected skills into `.agents/skills`
- **WHEN** the runtime builds a Gemini managed home with one or more selected skills
- **THEN** the projected Gemini skills are created under `.gemini/skills` in that managed home
- **AND THEN** the runtime does not target `.agents/skills` as the primary Gemini skills destination for that managed home

#### Scenario: Default Gemini join-time skill installation uses `.agents/skills`
- **WHEN** Houmao adopts a Gemini session and performs the default Houmao-owned skill projection for that session
- **THEN** the installed Gemini skills are created under the adopted session's `.gemini/skills` root
- **AND THEN** the default projection contract does not require a parallel mirror under `.agents/skills`

#### Scenario: Reused Gemini managed home removes the legacy alias root
- **WHEN** the runtime rebuilds or refreshes a Houmao-managed Gemini home that still contains Houmao-managed Gemini skill content under `.agents/skills`
- **THEN** the runtime removes the legacy Houmao-managed `.agents/skills` entries before or during projection into `.gemini/skills`
- **AND THEN** `.agents/skills` is not left behind as the maintained Houmao-managed Gemini skill root

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and persist manifest-backed mailbox bindings
When mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset through a discoverable tool-native mailbox skill surface and SHALL persist one transport-specific mailbox binding for that session in the session manifest.

When the selected transport is `filesystem`, the runtime SHALL derive and persist the effective filesystem mailbox content root and the mailbox identity needed to resolve current filesystem mailbox state for that session.

When the selected transport is `stalwart`, the runtime SHALL persist the real-mail mailbox binding metadata needed for later mailbox work and SHALL NOT synthesize filesystem-only mailbox path metadata that does not belong to that transport.

Those persisted Stalwart runtime bindings SHALL expose only secret-free transport metadata, with any session-local credential material derived later from persisted references rather than embedded inline in the session manifest.

When no explicit filesystem mailbox content root override is supplied, the runtime SHALL derive the effective filesystem mailbox content root from the independent Houmao mailbox root rather than from the effective runtime root.

When no explicit filesystem mailbox content root override is supplied and `HOUMAO_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the runtime SHALL derive the effective Houmao mailbox root from that env-var override before persisting or resolving filesystem mailbox state for that session.

When current filesystem mailbox resolution depends on the session address having an active mailbox registration, the runtime SHALL bootstrap or confirm that session's mailbox registration before persisting the durable mailbox binding or serving manager-owned current-mailbox resolution for `start-session`.

The runtime SHALL satisfy that registration-dependent mailbox contract through bootstrap ordering rather than by synthesizing fallback mailbox paths when the active registration is missing.

For Claude sessions, the discoverable tool-native mailbox skill surface SHALL use Claude-native top-level Houmao skill directories under the active isolated Claude skill root rather than a `mailbox/` namespace subtree.

For Claude sessions, the isolated Claude skill root SHALL remain part of the runtime-owned `CLAUDE_CONFIG_DIR` rather than being rebound to the launched workdir's `.claude/` directory.

For Codex and other non-Claude sessions whose active skill destination remains `skills`, the discoverable tool-native mailbox skill surface MAY continue to use the existing visible mailbox namespace subtree when that remains the active contract for that tool.

For Gemini sessions, the discoverable tool-native mailbox skill surface SHALL use top-level Houmao-owned skill directories under `.gemini/skills/` rather than `.gemini/skills/mailbox/...`.

#### Scenario: Start Claude session projects mailbox system skills with a filesystem mailbox binding
- **WHEN** a developer starts a Claude session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the Claude active skill destination through top-level Houmao-owned skill directories
- **AND THEN** the runtime persists one filesystem mailbox binding for that session in the session manifest
- **AND THEN** later mailbox discovery can derive the effective mailbox content root for that session from that persisted binding

#### Scenario: Start Claude session keeps runtime-owned state out of project-local `.claude`
- **WHEN** a developer starts a Claude session with mailbox support enabled for workdir `<workdir>`
- **THEN** the runtime uses an isolated runtime-owned `CLAUDE_CONFIG_DIR` for Houmao-managed Claude state
- **AND THEN** runtime-owned mailbox skill projection does not require setting `CLAUDE_CONFIG_DIR` to `<workdir>/.claude`
- **AND THEN** the runtime does not depend on projecting Houmao mailbox skills into the user repo's `.claude/skills/` tree

#### Scenario: Start Claude session projects mailbox system skills with a Stalwart mailbox binding
- **WHEN** a developer starts a Claude session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the Claude active skill destination through top-level Houmao-owned skill directories
- **AND THEN** the runtime persists one secret-free `stalwart` mailbox binding for that session in the session manifest
- **AND THEN** the runtime does not persist filesystem mailbox root or mailbox-path metadata for that Stalwart session

#### Scenario: Start Codex session projects mailbox system skills through its current visible mailbox namespace
- **WHEN** a developer starts a Codex session with mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skill destination through the current visible mailbox namespace for that tool
- **AND THEN** the runtime persists the transport-appropriate mailbox binding for that session in the session manifest

#### Scenario: Start Gemini session projects mailbox system skills through native top-level Houmao skill directories
- **WHEN** a developer starts a Gemini session with mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into `.gemini/skills/` through top-level Houmao-owned skill directories
- **AND THEN** the runtime does not rely on a `.gemini/skills/mailbox/...` namespace subtree for the maintained Gemini contract
- **AND THEN** the runtime persists the transport-appropriate mailbox binding for that session in the session manifest

#### Scenario: Start session defaults the filesystem mailbox root from the Houmao mailbox root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the persisted session mailbox binding reflects that derived default path

#### Scenario: Mailbox-root env-var override redirects the effective mailbox root
- **WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the persisted session mailbox binding reflects that env-var-derived mailbox root

#### Scenario: Start session bootstraps registration instead of synthesizing missing filesystem state
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **AND WHEN** current mailbox resolution would otherwise fail because the session address lacks an active mailbox registration
- **THEN** the runtime bootstraps or confirms the active mailbox registration before persisting the durable mailbox binding
- **AND THEN** it does not synthesize fallback mailbox paths just to satisfy later current-mailbox resolution
