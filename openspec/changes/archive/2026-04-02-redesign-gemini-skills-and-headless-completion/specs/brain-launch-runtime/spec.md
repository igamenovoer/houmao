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

For Codex and other non-Claude sessions whose active skill destination remains `skills`, the discoverable tool-native mailbox skill surface MAY continue to use the existing visible mailbox namespace subtree when that remains the active contract for that tool.

For Gemini sessions, the discoverable tool-native mailbox skill surface SHALL use top-level Houmao-owned skill directories under `.agents/skills/` rather than `.agents/skills/mailbox/...`.

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
- **THEN** the runtime projects the mailbox system skills for that session into `.agents/skills/` through top-level Houmao-owned skill directories
- **AND THEN** the runtime does not rely on a `.agents/skills/mailbox/...` namespace subtree for the maintained Gemini contract
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
- **AND THEN** the runtime does not synthesize fallback mailbox paths for that second session merely because registration-dependent state was not yet initialized

### Requirement: Tmux-backed headless turns reuse the primary agent window
For one tmux-backed headless session, runtime-controlled prompt execution SHALL be serialized and SHALL NOT overlap.

The runtime SHALL execute each runtime-controlled headless turn on the stable primary agent surface in window 0 and SHALL NOT create a separate per-turn tmux window for normal turn execution.

The runtime SHALL launch each runtime-controlled headless turn through a same-pane fresh-process execution primitive on the stable primary surface rather than typing the command into a long-lived interactive shell.

A runtime-controlled headless turn SHALL reach terminal state when the managed child process for that turn exits and the runtime persists that turn's durable terminal artifact state, including the exit-status artifact.

The runtime SHALL reconcile terminal headless turn status, terminal timestamps, and next-turn readiness from the authoritative active-turn record plus durable turn artifacts rather than from tmux shell redraw or idle-prompt posture on window 0.

After a runtime-controlled headless turn reaches terminal state, the runtime SHALL leave the stable primary surface attachable as the idle `agent` window for the next controlled turn.

Turn identity, stdout, stderr, exit status, and process metadata SHALL remain per-turn durable artifacts on disk rather than being encoded through tmux window allocation.

#### Scenario: Active headless turn runs on the primary agent surface
- **WHEN** the runtime starts a controlled turn for a tmux-backed headless session
- **THEN** that turn executes on the stable window-0 agent surface
- **AND THEN** rolling output remains visible on that same primary surface
- **AND THEN** the runtime does not create a separate per-turn tmux window for that turn

#### Scenario: Process exit finalizes terminal headless turn state
- **WHEN** the managed child process for a runtime-controlled tmux-backed headless turn exits
- **THEN** the runtime writes the durable terminal artifact state for that turn, including the exit-status artifact
- **AND THEN** the runtime treats that turn as terminal from those artifacts without waiting for an idle shell redraw on window 0
- **AND THEN** later inspection can reconcile that turn as completed or failed from the durable artifacts

#### Scenario: Primary agent surface remains reusable after a controlled turn completes
- **WHEN** a runtime-controlled headless turn completes on the stable primary surface
- **THEN** the runtime leaves window 0 attachable as the `agent` surface
- **AND THEN** the next controlled turn can reuse that same primary surface without allocating a new tmux window

#### Scenario: Runtime-controlled headless turns do not overlap in one session
- **WHEN** one runtime-controlled headless turn is already active for a tmux-backed session
- **AND WHEN** another runtime-controlled prompt is addressed to that same live session before the first turn reaches terminal state
- **THEN** the runtime does not start a second overlapping CLI execution for that session
- **AND THEN** window 0 remains the only runtime-controlled execution surface for that headless agent
