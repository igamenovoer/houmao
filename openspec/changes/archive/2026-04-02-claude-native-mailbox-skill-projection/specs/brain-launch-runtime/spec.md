## MODIFIED Requirements

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

For non-Claude sessions, the discoverable tool-native mailbox skill surface MAY continue to use the existing visible mailbox namespace subtree when that remains the active contract for that tool.

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

#### Scenario: Start non-Claude session projects mailbox system skills through its current visible mailbox namespace
- **WHEN** a developer starts a non-Claude agent session with mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skill destination through the current visible mailbox namespace for that tool
- **AND THEN** the runtime persists the transport-appropriate mailbox binding for that session in the session manifest

#### Scenario: Start session defaults the filesystem mailbox root from the Houmao mailbox root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the persisted session mailbox binding reflects that derived default path

#### Scenario: Mailbox-root env-var override redirects the effective mailbox root
- **WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the persisted session mailbox binding reflects that derived path

#### Scenario: Second mailbox-enabled session joins an initialized shared mailbox root without manual pre-registration
- **WHEN** one mailbox-enabled session has already initialized and registered itself into a shared filesystem mailbox root
- **AND WHEN** a second mailbox-enabled session starts against that same shared mailbox root with its own mailbox address
- **THEN** the runtime bootstraps or confirms the second session's mailbox registration before persisting registration-dependent filesystem mailbox state for that session
- **AND THEN** the second `start-session` succeeds without requiring manual mailbox pre-registration outside the runtime startup path
