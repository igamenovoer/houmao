# Q&A: add-agent-mailbox-protocol

## Introduction

This Q&A covers the `add-agent-mailbox-protocol` OpenSpec change and is intended for developers (including future maintainers) who need a concise place to track implementation questions and answers about the mailbox runtime, transport, and projected skills.

**Related docs**
- `openspec/changes/add-agent-mailbox-protocol/proposal.md`
- `openspec/changes/add-agent-mailbox-protocol/design.md`
- `openspec/changes/add-agent-mailbox-protocol/tasks.md`
- `openspec/changes/add-agent-mailbox-protocol/specs/agent-mailbox-fs-transport/spec.md`
- `openspec/changes/add-agent-mailbox-protocol/specs/brain-launch-runtime/spec.md`
- `context/issues/features/feat-filesystem-mailbox-principal-deregistration-cleanup.md`

**Key entrypoints and modules**
- `src/gig_agents/agents/brain_builder.py`
- `src/gig_agents/agents/brain_launch_runtime/runtime.py`
- `src/gig_agents/agents/brain_launch_runtime/mail_commands.py`
- `src/gig_agents/agents/mailbox_runtime_support.py`
- `src/gig_agents/mailbox/protocol.py`
- `src/gig_agents/mailbox/filesystem.py`
- `src/gig_agents/mailbox/managed.py`

## How does the filesystem-based email protocol work?
> Last revised at: `2026-03-12T04:42:44Z` | Last revised base commit: `975911b`

At a high level, one filesystem mailbox root contains the canonical messages, the mailbox views, the mutable SQLite state, and the managed helper surface:

```text
<mailbox_root>/
  protocol-version.txt                  # mailbox on-disk protocol version
  index.sqlite                          # mutable state: unread, starred, threads, attachments
  rules/                                # mailbox-local coordination surface
    README.md                           # human/agent guidance for this mailbox
    scripts/
      requirements.txt                  # Python deps for managed helper scripts
      deliver_message.py                # delivery commit helper
      insert_standard_headers.py        # optional header/front-matter normalizer
      update_mailbox_state.py           # read/star/archive state updater
      repair_index.py                   # repair/reindex helper
  locks/
    index.lock                          # serializes shared SQLite/index work
    principals/
      <principal>.lock                  # serializes mailbox mutations per principal
  messages/
    YYYY-MM-DD/
      <message-id>.md                   # canonical immutable Markdown message
  mailboxes/
    <principal>/
      inbox/                            # recipient-facing symlink projections
      sent/                             # sender-facing symlink projections
      archive/                          # reserved placeholder in v1
      drafts/                           # reserved placeholder in v1
  attachments/
    managed/                            # optional managed-copy attachments
  staging/                              # pre-commit write area
```

- Canonical message storage:

  ```text
  <mailbox_root>/
    messages/
      YYYY-MM-DD/
        <message-id>.md
  ```

  Each delivered message is written once as a Markdown file with YAML front matter for `message_id`, sender, recipients, thread ancestry, and attachments. This is the durable source of truth for message content, implemented around `src/gig_agents/mailbox/protocol.py`.

- Mailbox views for each participant:

  ```text
  <mailbox_root>/
    mailboxes/
      <principal>/
        inbox/
        sent/
        archive/
        drafts/
  ```

  A participant does not get a separate copied message body. Instead, `inbox/` and `sent/` contain symlinks back to the canonical file under `messages/`, so the same message can appear in multiple mailboxes without duplication. In v1, `archive/` and `drafts/` exist only as reserved placeholder directories.

- Mutable state and concurrency control:

  ```text
  <mailbox_root>/
    index.sqlite
    locks/
      index.lock
      principals/
        <principal>.lock
  ```

  Message bodies stay immutable after delivery, so read/unread, starred, archived, thread summaries, and attachment associations live in `index.sqlite`. Updates that touch shared state are coordinated with `index.lock` plus per-principal locks so concurrent writers do not corrupt mailbox state.

- Managed helper surface:

  ```text
  <mailbox_root>/
    rules/
      README.md
      scripts/
        requirements.txt
        deliver_message.py
        insert_standard_headers.py
        update_mailbox_state.py
        repair_index.py
  ```

  Agents are expected to inspect `rules/` first because that is the mailbox-local coordination surface. Sensitive operations are standardized through the managed scripts in `rules/scripts/`, and `requirements.txt` tells agents or operators which Python packages are needed before invoking those helpers. The implementation lives in `src/gig_agents/mailbox/filesystem.py` and `src/gig_agents/mailbox/managed.py`.

- Delivery flow and temporary writes:

  ```text
  <mailbox_root>/
    staging/
    messages/
    mailboxes/
  ```

  A new outgoing message is prepared in `staging/`, then committed into `messages/`, then projected into recipient `inbox/` folders and the sender `sent/` folder. At runtime, the live session gets mailbox bindings from `src/gig_agents/agents/mailbox_runtime_support.py`, and `mail check`, `mail send`, plus `mail reply` use the runtime-owned mailbox skill and the structured result parser in `src/gig_agents/agents/brain_launch_runtime/mail_commands.py`.

## From an agent's standpoint, how do I join an existing mail group?
> Last revised at: `2026-03-12T04:45:52Z` | Last revised base commit: `975911b`

- Join means "become a registered principal in an existing shared mailbox root." In practice, the session must be started against the existing group with a filesystem mailbox binding such as `--mailbox-transport filesystem`, `--mailbox-root <existing-mailbox-root>`, `--mailbox-principal-id <principal>`, and `--mailbox-address <address>` from `src/gig_agents/agents/brain_launch_runtime/cli.py`.

- If the agent is fine using an in-root mailbox, the runtime bootstrap path can register it directly:

  ```text
  <mailbox_root>/
    mailboxes/
      AGENTSYS-research/
        inbox/
        sent/
        archive/
        drafts/
  ```

  In that case, `bootstrap_filesystem_mailbox(..., principal=...)` creates the mailbox directories and inserts an `in_root` principal record in SQLite, as implemented in `src/gig_agents/mailbox/filesystem.py`.

- If the agent wants to keep its mailbox view outside the shared root, it joins by symlink registration:

  ```text
  <mailbox_root>/
    mailboxes/
      AGENTSYS-research -> /abs/path/private-mailboxes/AGENTSYS-research
  ```

  The symlink target must already exist and expose `inbox/`, `sent/`, `archive/`, and `drafts/`. The change spec treats this as the dynamic join path for an existing private mailbox directory rather than forcing every participant to relocate under the shared root.

- The shared mailbox still owns the canonical store and shared state even when the participant is symlink-registered:

  ```text
  <mailbox_root>/
    messages/
    index.sqlite
    locks/
    mailboxes/
      AGENTSYS-research -> /abs/path/private-mailboxes/AGENTSYS-research
  ```

  Delivery writes the canonical message under `messages/`, updates `index.sqlite`, and creates inbox or sent projections through the registered mailbox path. The participant's private mailbox directory externalizes the mailbox view, not the canonical corpus.

- The registration must validate cleanly before mail delivery works. If `mailboxes/<principal>` is missing, the symlink target is dangling, the target lacks the expected mailbox subdirectories, or the registered address does not match, managed delivery fails explicitly instead of silently creating a new mailbox at some other path. That validation path is enforced in `src/gig_agents/mailbox/managed.py`.

- Once the session is started and the registration is valid, the agent does not need a separate "join protocol" inside prompts. It simply sees the mailbox through the `AGENTSYS_MAILBOX_*` env vars and uses the runtime-owned mailbox skill or `mail check`, `mail send`, and `mail reply` against that already-joined mailbox root.

## When an agent leaves the group, what cleanup actions are needed in the current protocol?
> Last revised at: `2026-03-12T05:15:31Z` | Last revised base commit: `975911b`

- The current protocol does not define a first-class "leave group" or principal-deregistration workflow. I could find join semantics, delivery-time registration validation, and staging cleanup, but no spec or implementation contract for participant removal.

- What is missing:
  There is no documented rule for whether leaving should delete `mailboxes/<principal>`, remove or retain the `principals` row in `index.sqlite`, preserve old inbox or sent projections, keep historical mailbox state, or quarantine anything in the participant's private mailbox directory.

- What the current implementation does make clear:

  ```text
  <mailbox_root>/
    mailboxes/
      <principal>/
  ```

  or

  ```text
  <mailbox_root>/
    mailboxes/
      <principal> -> /abs/path/private-mailboxes/<principal>
  ```

  If that registration becomes missing or invalid, future delivery fails explicitly. The transport treats missing or dangling principal registrations as delivery-time errors rather than silently creating a replacement mailbox somewhere else.

- What is defined today is narrower cleanup around interrupted delivery, not participant departure:

  ```text
  <mailbox_root>/
    staging/
  ```

  The managed repair and cleanup flow can remove or quarantine orphaned staging artifacts from interrupted writes, but that is transport crash recovery, not a "leave the group" procedure.

- Minimal next step to confirm:
  We need a follow-up protocol decision that defines principal deregistration semantics for v1 or a later change, including whether leave means "stop future delivery only" or also "clean up mailbox views and registry state." That behavior should be specified before adding any automated cleanup command. The current feature-request placeholder for that work is `context/issues/features/feat-filesystem-mailbox-principal-deregistration-cleanup.md`.

- Where it should be documented:
  Add the authoritative leave or deregistration contract to `openspec/changes/add-agent-mailbox-protocol/specs/agent-mailbox-fs-transport/spec.md`, with the operational rationale and retention rules explained in `openspec/changes/add-agent-mailbox-protocol/design.md`.

## Does the current protocol provide scripts so agents can clean up consistently, or does an agent need to figure it out?
> Last revised at: `2026-03-12T05:15:31Z` | Last revised base commit: `975911b`

- The current protocol does provide managed scripts for consistent shared-mailbox operations, including some cleanup and repair work. The fixed v1 helper surface under `rules/scripts/` is:

  ```text
  <mailbox_root>/
    rules/
      scripts/
        deliver_message.py
        insert_standard_headers.py
        update_mailbox_state.py
        repair_index.py
        requirements.txt
  ```

  Those filenames are part of the protocol surface, so agents are not expected to invent their own raw SQLite or lock-file logic for the covered operations.

- For cleanup that is already defined by the transport, the consistent path is to use the managed helpers rather than figure it out ad hoc. In particular, `repair_index.py` covers repair or reindex work, and the managed implementation in `src/gig_agents/mailbox/managed.py` includes cleanup or quarantine of orphaned staging artifacts from interrupted deliveries.

- `update_mailbox_state.py` is also part of that standardization story, but it is for mailbox-state mutation such as read, starred, or archived flags, not for participant departure cleanup. `deliver_message.py` standardizes delivery commits, and `insert_standard_headers.py` is a reserved helper for message formatting consistency.

- Where the current protocol stops is leave-group cleanup. There is no managed script today for "agent deregistration," "remove this principal from the mail group," or "clean up this principal's mailbox registration and historical state." So for that specific scenario, the agent cannot rely on a defined cleanup script because the protocol has not defined one yet.

- That means the right behavior today is split:
  use the managed scripts for the cleanup or repair actions the protocol already defines, but do not guess a leave-group cleanup contract that the protocol does not define. If leave behavior matters, it needs a follow-up spec change and then a corresponding managed script or command surface; the proposed follow-up is tracked in `context/issues/features/feat-filesystem-mailbox-principal-deregistration-cleanup.md`.

## Does the current implementation force each agent to have a place in the mail group?
> Last revised at: `2026-03-12T05:25:19Z` | Last revised base commit: `975911b`

- Not for every agent globally. Mailbox participation is opt-in at build or start time: if a session does not resolve a mailbox config, it simply has no mailbox bindings, and runtime mailbox commands reject it as "not mailbox-enabled."

- For a mailbox-enabled session, yes, the implementation gives that session principal a concrete place in the mailbox group:

  ```text
  <mailbox_root>/
    mailboxes/
      <principal>/
        inbox/
        sent/
        archive/
        drafts/
  ```

  During session start or mailbox refresh, `bootstrap_resolved_mailbox()` calls `bootstrap_filesystem_mailbox(..., principal=...)`, and the current bootstrap implementation registers that principal as `in_root` and creates the mailbox directories under the shared root.

- Delivery also assumes every sender and recipient involved in one message has a valid mailbox registration. For recipients, managed delivery loads the principal registrations from `index.sqlite` and fails explicitly if a recipient principal is missing or invalid instead of creating an ad hoc mailbox on the fly.

- So the practical answer is:
  no, the system does not force every agent in the repo to join a mail group, but yes, once an agent session is mailbox-enabled the current implementation expects that principal to have a concrete registered mailbox place before mailbox traffic works.

- There is one implementation nuance to keep in mind:
  the change spec allows symlink-based principal registration in general, but the current runtime bootstrap path auto-registers the active session principal as an in-root mailbox. In other words, the implementation currently forces a concrete place for the active mailbox-enabled session principal, rather than keeping membership abstract.

## In the current implementation, when is the mailbox root created, and who is responsible for that?
> Last revised at: `2026-03-12T05:33:32Z` | Last revised base commit: `975911b`

- The mailbox root is not created during brain build. `src/gig_agents/agents/brain_builder.py` only records declarative mailbox config into the built manifest and projects the runtime-owned mailbox skill into the home; it does not create `mailbox_root` on disk.

- The actual filesystem mailbox root is created or validated when a mailbox-enabled runtime session starts:

  ```text
  start-session
    -> resolve_effective_mailbox_config(...)
    -> build_launch_plan(...)
    -> bootstrap_resolved_mailbox(...)
    -> bootstrap_filesystem_mailbox(...)
  ```

  That flow lives in `src/gig_agents/agents/brain_launch_runtime/runtime.py` and `src/gig_agents/agents/mailbox_runtime_support.py`.

- The lower-level owner of the on-disk creation work is `bootstrap_filesystem_mailbox()` in `src/gig_agents/mailbox/filesystem.py`. That function creates or validates the directory layout, writes or checks `protocol-version.txt`, materializes `rules/` and `rules/scripts/`, initializes `index.sqlite`, and optionally registers the active principal as an in-root mailbox.

- So the responsibility is layered:
  the runtime is responsible for deciding that mailbox support is enabled for this session and invoking bootstrap, while the mailbox filesystem module is responsible for actually creating or validating the mailbox root on disk.

- If the mailbox root already exists, the same bootstrap path still runs, but it behaves as validation plus completion rather than unconditional fresh creation. In other words, "create" here really means "create if missing, otherwise validate and materialize any required managed assets."

- The mailbox root can also be re-bootstraped later during mailbox binding refresh:

  ```text
  refresh_mailbox_bindings(...)
    -> refresh_filesystem_mailbox_config(...)
    -> bootstrap_resolved_mailbox(...)
  ```

  That matters when the runtime updates the effective filesystem mailbox root for an active session.

- The related config entries are what decide whether bootstrap will happen and where the root will live. In a recipe or built manifest, the declarative mailbox block looks like:

  ```yaml
  mailbox:
    transport: filesystem
    principal_id: AGENTSYS-research
    address: AGENTSYS-research@agents.localhost
    filesystem_root: shared-mail
  ```

  This block belongs in the brain recipe file under the `agents/` tree, not in the role prompt or tool-adapter file. In the current fixture layout, the recipe location pattern is:

  ```text
  tests/fixtures/agents/
    brains/
      brain-recipes/
        <tool>/
          <recipe>.yaml
  ```

  For example, a mailbox-enabled fixture recipe would live alongside paths such as `tests/fixtures/agents/brains/brain-recipes/codex/gpu-kernel-coder-default.yaml`.

  `transport: filesystem` is the important switch. If mailbox transport resolves to `filesystem`, runtime bootstrap creates or validates the mailbox root at session start. If mailbox config is absent, or transport resolves to `none`, no mailbox root is created for that session.

- The effective root location is resolved in this order:

  ```text
  start-session --mailbox-root <path>
    > mailbox.filesystem_root from recipe/manifest
    > default <runtime_root>/mailbox
  ```

  So `filesystem_root` in config tells the runtime where it should create or validate the mailbox root, `--mailbox-root` can override it for an ad hoc session, and if neither is present the runtime falls back to `<runtime_root>/mailbox`.

- The other mailbox config entries do not control whether the root is created, but they do affect how bootstrap registers the active principal once creation happens:
  `principal_id` sets the mailbox principal name, and `address` sets the email-like address. If they are omitted, the runtime derives defaults before calling bootstrap.

## Does the current implementation miss a unified config specification for shared resources such as shared mailboxes or CAO server launch settings?
> Last revised at: `2026-03-12T05:36:37Z` | Last revised base commit: `975911b`

- Yes, that gap appears real in the current implementation. Shared-resource configuration exists, but it is fragmented across different surfaces instead of being described by one shared config schema that agents, recipes, blueprints, and operators all reference consistently.

- Mailbox configuration currently lives in the brain recipe or built manifest:

  ```yaml
  mailbox:
    transport: filesystem
    principal_id: AGENTSYS-research
    address: AGENTSYS-research@agents.localhost
    filesystem_root: shared-mail
  ```

  That is session- or recipe-scoped configuration. It tells the runtime whether mailbox support is enabled and where the mailbox root should be bootstrapped, but it is not a reusable named "shared mailbox definition" that multiple recipes reference from one central source.

- CAO runtime connection settings live somewhere else again, mostly as runtime CLI flags and persisted session-manifest state:

  ```text
  start-session
    --cao-base-url http://localhost:9889
    --cao-profile-store <path>
    --cao-parsing-mode <mode>
  ```

  So the agent session knows how to talk to CAO, but those settings are not defined in the same config object as mailbox or other shared infrastructure.

- CAO server launch settings are separate from both of those and live in launcher TOML under `config/`:

  ```toml
  base_url = "http://localhost:9889"
  runtime_root = "tmp/agents-runtime"
  home_dir = "/data/agents/cao-home"
  proxy_policy = "clear"
  startup_timeout_seconds = 15
  ```

  That is an operator-facing service-launch config, not an `agents/` recipe-side shared resource definition.

- The practical result is that the repo has config knobs for shared things, but not a single shared-resource specification layer. Today we have:
  recipe-scoped mailbox config in `agents/brains/brain-recipes/...`,
  runtime CLI overrides for session startup,
  launcher TOML for CAO server process startup,
  mailbox-local operational rules inside the mailbox root itself under `rules/`.

- What seems missing is a central declarative place for reusable shared infrastructure objects, for example:
  named shared mailbox roots,
  named CAO service definitions,
  other shared runtime resources that multiple recipes or blueprints could reference indirectly instead of repeating concrete paths or URLs.

- So I would answer "yes, probably." The current implementation is functional, but it does not yet have one coherent config specification for shared resources across the `agents/` model and runtime tooling.

## If an agent already joined a mail group, how does `alice` send mail to `bob`?
> Last revised at: `2026-03-12T08:05:35Z` | Last revised base commit: `975911b`

- The supported current path is to run a runtime mail command against `alice`'s resumed session:

  ```bash
  pixi run python -m gig_agents.agents.brain_launch_runtime mail send \
    --agent-identity alice \
    --to AGENTSYS-bob \
    --subject "Hello Bob" \
    --instruction "Send Bob a short hello message and ask for status."
  ```

  That asks the live `alice` session to use the runtime-owned mailbox skill and send one mailbox message.

- If `alice`'s mailbox principal is not literally `alice`, use the actual registered mailbox principal or address. In the current implementation, default mailbox principal ids for named agents are often prefixed into the `AGENTSYS-...` namespace, so `bob` may actually need to be addressed as `AGENTSYS-bob` or `AGENTSYS-bob@agents.localhost`.

- In the current implementation, treat `--to` as needing the full registered mailbox identity, not a casual agent nickname. The CLI accepts a plain string like `bob`, but it does not normalize that into `AGENTSYS-bob` for you, so the safe forms are the full principal id or full mailbox address.

- You can also provide a message body from a file instead of an inline instruction:

  ```bash
  pixi run python -m gig_agents.agents.brain_launch_runtime mail send \
    --agent-identity alice \
    --to AGENTSYS-bob \
    --subject "Hello Bob" \
    --body-file /abs/path/to/message.md
  ```

  The CLI requires either `--instruction` or `--body-file` for `mail send`.

- `--instruction` is not a fixed built-in function selector. In the current implementation it is passed into the mailbox request as operator guidance to the live agent session, telling the agent what mail it should compose or send. By contrast, `--body-file` becomes explicit `body_markdown` content that is surfaced directly in the request payload.

- So semantically:

  ```text
  --instruction "Send Bob a short hello message and ask for status."
  ```

  means "ask the agent to compose and send a message with that intent," not "invoke a predefined send-hello function." If you want the message body to be explicit and operator-authored rather than agent-composed from instructions, use `--body-file`.

- This only works if all of the following are already true:
  `alice`'s session is mailbox-enabled, `alice` is already running or resumable by `--agent-identity`, and `bob` already has a valid mailbox registration in the same shared mailbox root. Managed delivery fails explicitly if the recipient principal registration is missing or invalid.

- Conceptually, the send flow is:

  ```text
  alice session
    -> runtime mail send
    -> projected mailbox skill prompt
    -> managed delivery helper
    -> canonical message in messages/<date>/<message-id>.md
    -> inbox symlink under bob's mailbox
  ```

  So `alice` does not hand-edit the mailbox directly in the common path; the runtime tells the live session to perform the mailbox action and then validates the structured result.

## In the `--to <who>` CLI argument, can we omit the `AGENTSYS-` prefix?
> Last revised at: `2026-03-12T07:56:46Z` | Last revised base commit: `975911b`

- The CLI parser will accept it syntactically, because `--to` values are taken as plain strings:

  ```text
  mail send --to bob
  ```

  There is no CLI-side validation that forces `AGENTSYS-...` at argument parse time.

- But the current implementation does not normalize recipient names for you. The runtime passes `--to` values through verbatim into the mailbox request payload:

  ```json
  {
    "args": {
      "to": ["bob"]
    }
  }
  ```

  So the system does not automatically rewrite `bob` into `AGENTSYS-bob`.

- In practice, that means omitting the prefix is not something you should rely on. Managed mailbox delivery expects recipient principals to match actual registered mailbox principals and addresses, and those are commonly stored in the `AGENTSYS-...` namespace.

- The safe forms to use are:

  ```text
  --to AGENTSYS-bob
  ```

  or

  ```text
  --to AGENTSYS-bob@agents.localhost
  ```

  depending on how that recipient is registered in the shared mailbox.

- So the short answer is:
  yes, you can omit the prefix at the raw CLI parsing level, but no, the current implementation does not guarantee that `bob` will be resolved automatically. Use the full registered principal or address if you want predictable delivery.

## How does an agent find out another agent's actual mail directory from a given mail address?
> Last revised at: `2026-03-12T08:22:11Z` | Last revised base commit: `975911b`

- In the current protocol, that is not really meant to be a first-class agent-facing step. Agents are supposed to address recipients by mailbox principal and email-like address, then rely on the shared mailbox registration and managed helpers to resolve the real mailbox path.

- The current agent-facing env contract only exposes the current session's own mailbox bindings, for example:

  ```text
  AGENTSYS_MAILBOX_ADDRESS
  AGENTSYS_MAILBOX_FS_ROOT
  AGENTSYS_MAILBOX_FS_INBOX_DIR
  ```

  It does not expose a general "lookup any other participant's mailbox dir by address" API.

- Under the hood, the shared mailbox does record the mapping in the principal registry inside `index.sqlite`:

  ```text
  principals(
    principal_id,
    address,
    mailbox_kind,
    mailbox_path
  )
  ```

  and the managed delivery code reads that registry to find the real mailbox path. But that lookup is currently keyed by `principal_id`, with an address-consistency check, not by a standardized address-only resolver exposed to agents.

- So if an agent knows only a mail address, the current protocol does not define a clean, first-class address-to-mailbox-dir lookup step for it. The intended flow is:
  know or resolve the recipient's full mailbox identity,
  use the shared mailbox helpers,
  let the managed layer resolve the actual `mailbox_path`.

- If an agent were to inspect the shared mailbox internals directly, the relevant information lives in `index.sqlite` and the `mailboxes/` registration tree, but that is more of an implementation detail than a documented agent contract. There is no dedicated managed script today whose job is "given this address, tell me the recipient mailbox directory."

- So the practical answer is:
  an agent should not assume it can or should derive another agent's actual mail dir directly from the address. In the current implementation, directory resolution is a shared-mailbox registry concern handled by the managed transport layer, not a stable standalone agent lookup contract.

## If an agent wants to join a mail group but finds its directory entry already exists, what happens?
> Last revised at: `2026-03-12T08:28:45Z` | Last revised base commit: `975911b`

- There are a few different cases here, and the current implementation treats them differently.

- Case 1: the existing entry is really the same principal from a prior run, with the same registered path and address.

  ```text
  principals:
    principal_id = AGENTSYS-alice
    mailbox_kind = in_root
    mailbox_path = <mailbox_root>/mailboxes/AGENTSYS-alice
    address = AGENTSYS-alice@agents.localhost
  ```

  In this case, bootstrap is effectively idempotent. `bootstrap_filesystem_mailbox(..., principal=...)` sees the existing SQLite principal row, confirms the same path and address, and returns successfully. This is the clean crash-recovery or restart-friendly case.

- Case 2: the same `principal_id` is already registered in SQLite, but with a different address or different mailbox path.

  ```text
  AGENTSYS-alice
    -> already registered at a different mailbox path
  ```

  or

  ```text
  AGENTSYS-alice
    -> already registered with a different address
  ```

  In that case, bootstrap fails explicitly with `MailboxBootstrapError`. So if the principal name is already taken by a conflicting registration, the current implementation does not silently overwrite it.

- Case 3: the filesystem directory already exists under `mailboxes/<principal>`, but there is no conflicting SQLite registration row yet.

  ```text
  <mailbox_root>/
    mailboxes/
      AGENTSYS-alice/
  ```

  This is the subtle case. The current bootstrap code creates the placeholder subdirectories with `exist_ok=True` before it checks SQLite. If no row exists yet for that `principal_id`, it inserts one and effectively adopts that existing directory path as the mailbox for the joining principal.

- That means the current implementation protects principal-name collisions primarily through the SQLite registry, not through a strong filesystem ownership check on the directory entry itself. If a stale or manually created directory already exists without a conflicting SQLite row, bootstrap does not currently distinguish "this was my old mailbox dir" from "someone else happened to create this path first."

- For symlink-based registrations, later managed delivery does validate the registration more strictly:
  it checks that a symlink-registered principal still has a real symlink entry under `mailboxes/<principal>` and that the target exposes the expected mailbox subdirectories. Missing or broken symlink targets fail explicitly at delivery time rather than being silently replaced.

- So the practical answer is:
  same-principal restart with matching SQLite registration works,
  conflicting existing registration fails,
  but a bare pre-existing directory entry without a conflicting SQLite row can be adopted by the joining principal in the current implementation. That last case is probably looser than an ideal ownership model.
