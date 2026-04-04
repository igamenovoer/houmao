## ADDED Requirements

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and persist manifest-backed mailbox bindings
When mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset under the reserved runtime-owned mailbox namespace and SHALL persist one transport-specific mailbox binding for that session in the session manifest.

When the selected transport is `filesystem`, the runtime SHALL derive and persist the effective filesystem mailbox content root and the mailbox identity needed to resolve current filesystem mailbox state for that session.

When the selected transport is `stalwart`, the runtime SHALL persist the real-mail mailbox binding metadata needed for later mailbox work and SHALL NOT synthesize filesystem-only mailbox path metadata that does not belong to that transport.

Those persisted Stalwart runtime bindings SHALL expose only secret-free transport metadata, with any session-local credential material derived later from persisted references rather than embedded inline in the session manifest.

When no explicit filesystem mailbox content root override is supplied, the runtime SHALL derive the effective filesystem mailbox content root from the independent Houmao mailbox root rather than from the effective runtime root.

When no explicit filesystem mailbox content root override is supplied and `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the runtime SHALL derive the effective Houmao mailbox root from that env-var override before persisting or resolving filesystem mailbox state for that session.

When current filesystem mailbox resolution depends on the session address having an active mailbox registration, the runtime SHALL bootstrap or confirm that session's mailbox registration before persisting the durable mailbox binding or serving manager-owned current-mailbox resolution for `start-session`.

The runtime SHALL satisfy that registration-dependent mailbox contract through bootstrap ordering rather than by synthesizing fallback mailbox paths when the active registration is missing.

#### Scenario: Start session projects mailbox system skills with a filesystem mailbox binding
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skills destination under the reserved runtime-owned namespace
- **AND THEN** the runtime persists one filesystem mailbox binding for that session in the session manifest
- **AND THEN** later mailbox discovery can derive the effective mailbox content root for that session from that persisted binding

#### Scenario: Start session projects mailbox system skills with a Stalwart mailbox binding
- **WHEN** a developer starts an agent session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skills destination under the reserved runtime-owned namespace
- **AND THEN** the runtime persists one secret-free `stalwart` mailbox binding for that session in the session manifest
- **AND THEN** the runtime does not persist filesystem mailbox root or mailbox-path metadata for that Stalwart session

#### Scenario: Start session defaults the filesystem mailbox root from the Houmao mailbox root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the persisted session mailbox binding reflects that derived default path

#### Scenario: Mailbox-root env-var override redirects the effective mailbox root
- **WHEN** `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the persisted session mailbox binding reflects that derived path

#### Scenario: Second mailbox-enabled session joins an initialized shared mailbox root without manual pre-registration
- **WHEN** one mailbox-enabled session has already initialized and registered itself into a shared filesystem mailbox root
- **AND WHEN** a second mailbox-enabled session starts against that same shared mailbox root with its own mailbox address
- **THEN** the runtime bootstraps or confirms the second session's mailbox registration before persisting registration-dependent filesystem mailbox state for that session
- **AND THEN** the second `start-session` succeeds without requiring manual mailbox pre-registration outside the runtime startup path

### Requirement: Runtime filesystem mailbox resolution follows the active mailbox registration path
When the runtime resolves current mailbox state for a filesystem-backed session, it SHALL derive registration-dependent filesystem paths from the active mailbox registration for the session's bound mailbox address rather than by reconstructing a mailbox path from `principal_id`.

At minimum, the manager-owned current-mailbox resolution path SHALL report the active inbox path for the session's bound mailbox address when that address has an active registration.

If runtime bootstrap or later current-mailbox resolution can detect that the target mailbox root still uses the unsupported principal-keyed layout from the earlier implementation, it SHALL fail explicitly and direct the operator to delete and re-bootstrap that mailbox root.

#### Scenario: Current mailbox resolution reports the active address-based inbox path
- **WHEN** the runtime resolves current mailbox state for a filesystem-backed session whose active registration is `AGENTSYS-research@agents.localhost`
- **THEN** the resolved inbox path points at the inbox for that active registration
- **AND THEN** the runtime does not derive that path by concatenating `mailboxes/<principal_id>/inbox`

#### Scenario: Updated registration changes derived filesystem mailbox paths
- **WHEN** the runtime resolves current mailbox state for an active filesystem-backed session after the active mailbox registration changes for the bound address
- **THEN** the resolved filesystem mailbox paths follow the current active registration for that address
- **AND THEN** subsequent runtime-controlled mailbox work uses the refreshed derived path set

#### Scenario: Unsupported stale mailbox root fails current mailbox resolution explicitly
- **WHEN** the runtime attempts to bootstrap or resolve current filesystem mailbox state against a stale principal-keyed mailbox root from the earlier implementation
- **THEN** the runtime fails explicitly
- **AND THEN** the error tells the operator to delete and re-bootstrap the mailbox root rather than silently deriving incorrect paths

## REMOVED Requirements

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and mailbox env bindings
**Reason**: Mailbox-specific `AGENTSYS_MAILBOX_*` env publication is no longer part of the mailbox runtime contract. The durable session mailbox binding remains authoritative, and current mailbox data is derived through manager-owned resolution instead of ambient mailbox env.
**Migration**: Persist mailbox capability in the session manifest, project mailbox system skills normally, and obtain current mailbox details through `houmao-mgr agents mail resolve-live` rather than expecting `AGENTSYS_MAILBOX_*` launch or tmux env keys.

### Requirement: Runtime sessions support filesystem mailbox binding refresh
**Reason**: The mailbox runtime no longer maintains a filesystem mailbox env-refresh contract for active sessions.
**Migration**: Use manifest-backed mailbox mutation and current-mailbox resolution so later mailbox work recomputes derived filesystem data from the persisted mailbox binding instead of refreshing mailbox env.

### Requirement: Tmux-backed sessions publish live-refreshable mailbox bindings into tmux session environment
**Reason**: Tmux session env is no longer a mailbox authority layer. Mailbox actionability is derived from the persisted mailbox binding plus transport validation, not from mailbox-specific tmux env projection.
**Migration**: Keep using tmux env only for session discovery pointers such as `AGENTSYS_MANIFEST_PATH`, and use manifest-backed mailbox resolution for late registration, status, and notifier readiness.

### Requirement: Runtime filesystem mailbox env bindings follow the active mailbox registration path
**Reason**: The active-registration rule still applies, but it now governs derived filesystem mailbox resolution rather than mailbox env publication.
**Migration**: Consume resolver-derived filesystem mailbox paths instead of `AGENTSYS_MAILBOX_FS_*` env values.
