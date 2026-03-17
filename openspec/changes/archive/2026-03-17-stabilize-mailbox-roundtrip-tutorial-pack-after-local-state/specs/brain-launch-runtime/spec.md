## MODIFIED Requirements

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and mailbox env bindings
When filesystem mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset under a reserved runtime-owned namespace and SHALL populate the filesystem mailbox binding env contract before mailbox-related work is expected from the agent.

When no explicit filesystem mailbox content root override is supplied, the runtime SHALL derive the effective filesystem mailbox content root from the independent Houmao mailbox root rather than from the effective runtime root.

When no explicit filesystem mailbox content root override is supplied and `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the runtime SHALL derive the effective Houmao mailbox root from that env-var override before publishing `AGENTSYS_MAILBOX_FS_ROOT`.

When active filesystem mailbox env bindings depend on the current session address having an active mailbox registration, the runtime SHALL bootstrap or confirm that session's mailbox registration before deriving those env bindings for `start-session`.

The runtime SHALL satisfy that registration-dependent env-binding contract through bootstrap ordering rather than by synthesizing fallback mailbox paths when the active registration is missing.

#### Scenario: Start session projects mailbox system skills with filesystem bindings
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skills destination under the reserved runtime-owned namespace
- **AND THEN** the runtime starts the session with the filesystem mailbox binding env vars needed by those mailbox system skills
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to the effective mailbox content root for that session

#### Scenario: Start session defaults filesystem mailbox root from the Houmao mailbox root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived default path

#### Scenario: Mailbox-root env-var override redirects the effective mailbox root
- **WHEN** `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived path

#### Scenario: Second mailbox-enabled session joins an initialized shared mailbox root without manual pre-registration
- **WHEN** one mailbox-enabled session has already initialized and registered itself into a shared filesystem mailbox root
- **AND WHEN** a second mailbox-enabled session starts against that same shared mailbox root with its own mailbox address
- **THEN** the runtime bootstraps or confirms the second session's mailbox registration before deriving registration-dependent filesystem mailbox env bindings
- **AND THEN** the second `start-session` succeeds without requiring manual mailbox pre-registration outside the runtime startup path
