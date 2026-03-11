## Why

Current agent coordination in this project is centered on direct terminal input, ad hoc handoff artifacts, and provider-specific session control. That works for tightly coupled flows, but it does not provide a durable async communication model that lets agents respond later, lets humans participate naturally, or cleanly spans both local-only and server-backed deployments.

We need a mailbox-style protocol now because multi-agent workflows are becoming more stateful and long-lived. A shared email-alike model gives us a familiar mental model for agents and humans while preserving an offline-first path that does not require a daemon.

We also need the mailbox surface to be runtime-owned rather than hand-authored per role. If every agent or role has to bake in mailbox paths, URLs, or addresses manually, those instructions will drift as bindings change and the same agent will behave differently across filesystem and email-backed deployments.

## What Changes

- Add a new async mailbox communication model for agent-to-agent, human-to-agent, and agent-to-human messaging.
- Define a canonical message protocol with email-like semantics, including addressing, message identifiers, threading, replies, attachments, delivery metadata, and per-recipient status.
- Add a filesystem-backed mailbox flavor that stores messages as Markdown files, indexes metadata and mutable status in SQLite, uses filesystem locking instead of a background service, resolves its mailbox content root from runtime-managed env bindings rather than a fixed run-directory path, allows participants to join a mail group by linking private mailbox dirs into the shared mail root, and publishes shared mailbox rules under `rules/` for standardized mailbox interaction. The runtime initializes that mailbox root directly through package-internal bootstrap code, materializes a fixed managed `rules/scripts/` set for sensitive SQLite or lock-touching operations plus optional header-normalization assistance, versions that managed script set with `protocol-version.txt`, and treats `archive/` and `drafts/` as reserved placeholder directories rather than defined v1 workflows.
- Define standard-email-compatible semantics and mappings so the filesystem-first protocol is easy to adapt to a future true email transport without implementing that transport in this change.
- Add runtime-generated system mailbox skills from platform-owned templates so every launched agent gets the same mailbox operating instructions without depending on role-specific authored skills.
- Add a runtime `mail` subcommand that asks a live agent session to perform mailbox operations such as `check`, `send`, and `reply` by explicitly telling the agent to use the injected mailbox skill by name, with mailbox metadata appended in the prompt instead of relying on ad hoc free-form prompts.
- Add a stable mailbox environment-binding contract so generated mailbox skills resolve transport-specific paths, URLs, and mailbox addresses through runtime-managed env vars that are populated at session start and refreshable on demand.
- Define periodic polling and response expectations so agents can check inboxes, process new messages asynchronously, and publish replies without requiring synchronous rendezvous.
- Make human participation a first-class part of the design so the same conversations can be inspected, authored, and resumed outside a single agent runtime.

## Capabilities

### New Capabilities

- `agent-mailbox-protocol`: Canonical message envelope, addressing, threading, attachment reference, and status semantics shared by all mailbox transports.
- `agent-mailbox-fs-transport`: Filesystem-native mailbox transport using directories, Markdown message files, SQLite indexes, and lock-file synchronization with no daemon requirement.
- `agent-mailbox-email-compatibility`: Canonical header mappings, threading semantics, and reserved env namespaces that keep the filesystem-first protocol easy to adapt to a future true email transport.
- `agent-mailbox-system-skills`: Runtime-generated system mailbox skills and env-var binding contracts that give every agent a consistent mailbox interface across transports.

### Modified Capabilities

- `brain-launch-runtime`: Session startup and runtime controls gain filesystem-mailbox system-skill injection, an agent-mediated `mail` subcommand for mailbox operations, plus runtime-managed filesystem mailbox env binding refresh for active sessions.

## Impact

This change is expected to affect agent orchestration flows, session and identity integration, runtime storage layout, runtime-owned skill injection, runtime CLI behavior, and operator-facing documentation. It will introduce a relocatable filesystem mailbox content root with a runtime-root default, symlink-based mail-group membership for private mailbox dirs, a shared `rules/` subtree for mailbox-local protocol guidance, standardized helper scripts for sensitive mailbox mutations, optional header-normalization helper scripts, a persistent SQLite index, generated system skill templates, an agent-mediated `mail` command surface, filesystem mailbox env-binding controls, and compatibility documentation that preserves a clean path to a future true email adapter without implementing it now.
