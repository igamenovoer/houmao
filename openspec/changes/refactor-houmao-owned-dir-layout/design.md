## Context

Houmao currently has several partially overlapping directory concepts:

- the shared discovery registry already lives under `~/.houmao/registry/` and is intentionally pointer-oriented,
- runtime-owned manifests and gateway state default to repo-local `tmp/agents-runtime/`,
- launcher-managed CAO artifacts currently live under a configurable `runtime_root/cao-server/<host>-<port>/`,
- filesystem mailbox state defaults to a path derived from the runtime root,
- agent working directories act as the CLI startup cwd but do not yet have a standardized per-agent job dir with clear destructive-edit semantics.

That layout grew incrementally. It works, but it no longer reflects the cleaner boundary we now have after the CAO workdir/home separation: CAO home does not need to own the agent workdir, and the registry does not need to pretend to be a general-purpose runtime state store.

This change is therefore a filesystem-ownership refactor. It needs one cross-cutting model that runtime, launcher, registry, mailbox, and docs all use consistently.

## Goals / Non-Goals

**Goals:**
- Define one explicit four-zone Houmao directory model:
  - `~/.houmao/registry` for discovery metadata,
  - `~/.houmao/runtime` for durable Houmao-owned runtime and launcher state,
  - `~/.houmao/mailbox` for the default shared mailbox root,
  - `<working-directory>/.houmao/jobs/<session-id>/` for agent-facing per-session scratch state.
- Keep directory hierarchy mechanics separate from agent grouping semantics, so agent association is discoverable from canonical agent name, authoritative `agent_id`, session metadata, and existing discovery surfaces rather than from tool- or family-bucket paths.
- Whenever a Houmao-owned directory is named after one agent, use authoritative `agent_id` as the directory name rather than canonical agent name.
- Replace registry-specific `agent_key` with cross-module `agent_id` as the authoritative agent identity.
- Keep the registry secret-free and pointer-oriented instead of turning it into mutable CAO or runtime storage.
- Move default runtime-owned session roots and launcher-managed CAO artifacts into the Houmao runtime root.
- Introduce a standardized per-agent job dir with explicit “safe for destructive session-local edits” semantics.
- Provide env-var overrides for Houmao-owned directory locations so CI and dynamic environments can relocate defaults without editing checked-in config files.
- Keep explicit overrides functional so CI, tests, and advanced operators can still relocate roots when needed.
- Stop relying on canonical agent name as the tmux session name or unique live lookup key; the true canonical name for a live session must be recoverable from persisted manifest metadata or the shared registry.
- Preserve compatibility for already-created manifests and runtime roots by continuing to honor explicit existing paths during resume/control.

**Non-Goals:**
- Auto-migrating old runtime roots, old mailbox roots, or previously built brain homes into the new defaults.
- Moving the mailbox subsystem under the registry or runtime roots as an ownership dependency.
- Turning the shared registry into a generalized metadata database for all Houmao subsystems.
- Redesigning mailbox transport internals, gateway queue internals, or CAO parsing behavior in the same change.
- Adding CAO server discovery publication under the registry in this change.

## Decisions

### 1. Adopt a four-zone Houmao-owned directory model

**Choice:** Standardize on four distinct filesystem zones with different lifecycles and mutability rules:

- `~/.houmao/registry`: discovery-only metadata
- `~/.houmao/runtime`: durable Houmao-managed control state
- `~/.houmao/mailbox`: default shared mailbox content root
- `<working-directory>/.houmao/jobs/<session-id>/`: per-agent job dir

The effective locations for those defaults may also be relocated through env-var overrides:
- registry root: existing `AGENTSYS_GLOBAL_REGISTRY_DIR`
- runtime root: `AGENTSYS_GLOBAL_RUNTIME_DIR`
- mailbox root: `AGENTSYS_GLOBAL_MAILBOX_DIR`
- local jobs dir: `AGENTSYS_LOCAL_JOBS_DIR`, which relocates per-session job dirs to `<local-jobs-dir>/<session-id>/`

Rationale:
- The current system already implicitly distinguishes these responsibilities, but only by convention.
- Separating them makes ownership easier to document and enforce.
- It gives operators a predictable “what can I delete?” model.
- It gives agents a clear destructive scratch area inside the project workspace without relocating the durable runtime session record into the project tree.
- Env-var relocation keeps those defaults practical in CI, tests, ephemeral sandboxes, and dynamic launch environments where the normal home- or workspace-derived paths are not appropriate.

Alternatives considered:
- *Keep the current repo-local `tmp/agents-runtime` default model* — rejected because it keeps durable runtime state tied to whatever repo or cwd the operator happened to use.
- *Put everything under `~/.houmao/registry`* — rejected because the registry is intentionally small, secret-free, and pointer-oriented.
- *Put all session-local state under the working directory only* — rejected because durable runtime control state and shared mailbox state should not depend on one project workspace remaining intact.

Representative target layout, intentionally detailed down to Houmao-managed files and known CAO-managed subtrees:

```text
~/.houmao/
  registry/
    live_agents/
      <agent-id>/
        record.json                       # Houmao shared-registry discovery record for one authoritative agent id, canonical name, and live tmux handle

  runtime/
    homes/
      <home-id>/
        config.toml                       # Houmao-projected agent runtime config
        launch.sh                         # Houmao launch helper
        .system/
          ...                             # Houmao-projected runtime-owned skills/assets
    manifests/
      <home-id>.yaml                      # Houmao built brain manifest

    sessions/
      <runtime-backend>/
        <session-id>/
          manifest.json                   # Houmao durable session record with canonical agent name, authoritative agent_id, and actual tmux session name
          gateway/
            attach.json                   # Houmao stable gateway attach contract
            state.json                    # Houmao last-known gateway state
            desired-config.json           # Houmao desired gateway config
            queue.sqlite                  # Houmao gateway durable queue
            events.jsonl                  # Houmao gateway durable event log
            logs/
              gateway.log                 # Houmao gateway service log
            run/
              current-instance.json       # Houmao live gateway instance pointer
              gateway.pid                 # Houmao live gateway pid tracking

    cao_servers/
      localhost-9889/
        launcher/
          cao-server.pid                  # Houmao launcher tracking
          cao-server.log                  # Houmao launcher-captured server stdout/stderr
          ownership.json                  # Houmao launcher ownership record
          launcher_result.json            # Houmao launcher diagnostics/result payload
        home/
          .aws/
            cli-agent-orchestrator/
              agent-store/
                <profile-name>.md         # Houmao-installed CAO profile markdown
              logs/
                terminal/
                  <terminal-id>.log       # CAO-created terminal log
              ...                         # other CAO-created state under HOME

  mailbox/
    protocol-version.txt                 # Houmao mailbox bootstrap marker
    index.sqlite                         # Houmao mailbox mutable state index
    messages/
    mailboxes/
    locks/
    rules/
    staging/

/repo/app/
  ...                                   # project files generally editable by the agent
  .houmao/
    jobs/
      <session-id>/
        logs/
        outputs/
        tmp/
        scratch/
        notes/
```

Important boundary notes:
- `registry/` is only for discovery metadata and pointers.
- `runtime/` is Houmao-owned durable control state.
- `runtime/cao_servers/.../home/.aws/cli-agent-orchestrator/` is CAO `HOME`, so it contains both Houmao-seeded files such as installed agent profiles and CAO-created runtime state such as terminal logs.
- `runtime/homes/` and `runtime/manifests/` stay intentionally flat in this design; agent grouping should come from persisted metadata, canonical agent name, authoritative `agent_id`, and other explicit identity metadata rather than from bucket names in the directory hierarchy.
- If a Houmao-owned subtree later introduces a directory keyed by one agent rather than by session or service instance, that directory name should use `agent_id`, not canonical agent name.
- tmux session names are live-session handles rather than authoritative agent names. To learn the true canonical agent name or authoritative `agent_id` for a live session, inspect persisted manifest metadata or shared-registry publication rather than parsing the tmux session name.
- Explicit CLI/config overrides still take precedence over env-var overrides; env-var overrides take precedence over the built-in default locations.
- `<working-directory>/.houmao/jobs/<session-id>/` is the per-agent destructive scratch area for that session, not the durable runtime session root.

### 2. Keep the registry as a locator layer, not as mutable runtime or CAO state

**Choice:** Preserve `~/.houmao/registry` as the home of discovery-oriented records only, with `live_agents/` remaining the current required namespace. Mutable runtime session state, launcher artifacts, CAO home state, and task logs stay outside the registry.

Rationale:
- This matches the current registry contract and avoids blurring the line between “find the live thing” and “own the live thing.”
- It keeps registry cleanup simple and safe.
- It avoids storing secrets, provider-specific home state, or noisy logs under the same root used for name-based discovery.

Alternatives considered:
- *Use `registry/cao_servers/...` as the actual CAO mutable home* — rejected because it would mix pointer-oriented registry state with launcher-owned mutable CAO state.
- *Replace the live-agent registry with runtime-root scanning* — rejected because cross-runtime-root discovery is one of the main reasons the registry exists.

### 3. Make the Houmao runtime root the durable state home for runtime sessions and CAO launcher-managed services

**Choice:** Default new runtime-owned state to `~/.houmao/runtime/`, with:

- generated homes under `~/.houmao/runtime/homes/<home-id>/`
- generated manifests under `~/.houmao/runtime/manifests/<home-id>.yaml`
- session roots under `~/.houmao/runtime/sessions/<backend>/<session-id>/`
- launcher-managed CAO service roots under `~/.houmao/runtime/cao_servers/<host>-<port>/`
- launcher artifacts under `.../launcher/`
- launcher-default CAO `HOME` under `.../home/`

Explicit runtime-root and `home_dir` overrides remain supported.

Rationale:
- A single durable Houmao runtime root makes runtime and launcher state easier to inspect and clean up.
- It preserves the distinction between runtime control state and agent-editable project state.
- It gives the launcher a deterministic default CAO home without forcing operators to hand-manage that path in every config.
- It avoids baking current tool or family categories into the on-disk layout for generated agent homes and manifests.

Alternatives considered:
- *Keep launcher artifacts under `runtime_root/cao-server/<host>-<port>/` forever* — rejected because the singular path name and flat layout make it awkward to colocate both launcher artifacts and default CAO home state cleanly.
- *Require explicit launcher `home_dir` forever* — rejected because the new ownership model should have a usable system-owned default.
- *Keep generated homes and manifests grouped by tool or family* — rejected because agent grouping is a higher-level identity concern that should be discoverable from metadata rather than frozen into directory buckets.

### 4. Treat canonical agent name as a strong human-facing label, `agent_id` as the authoritative global identity, and tmux session name as a live-session handle

**Choice:** Keep the directory layout mechanically simple while adopting a two-layer identity model for association:

- canonical agent name remains the strong human-facing label used for normal operator references, but it is no longer assumed to be globally unique,
- `agent_id` replaces registry-specific `agent_key` and becomes the authoritative globally unique per-agent identity for system-owned association and liveness publication,
- when no explicit `agent_id` is supplied and no previously persisted `agent_id` exists for the same built or resumed agent, the runtime bootstraps the initial `agent_id` as the full lowercase `md5(canonical agent name).hexdigest()`,
- once an `agent_id` has been persisted in build metadata, manifest metadata, or other runtime-owned agent metadata, later build, start, resume, or rename-like flows reuse that `agent_id` instead of recomputing it from the current canonical name,
- if an operator deliberately reuses one `agent_id` for different canonical names, the system warns but still treats that `agent_id` as the authoritative identity, and any resulting writable-state conflicts are user fault,
- if different agents happen to share the same canonical name, that name becomes an ambiguous lookup handle and `agent_id` remains the authoritative disambiguator,
- tmux session names are unique live-session handles and must not be treated as authoritative canonical agent names or as the source of truth for `agent_id`.

This means:
- the directory hierarchy does not need a `tool/`, `family/`, or per-agent bucket just to explain who an agent is,
- system-owned writable association can rely on `agent_id` without pretending that rare human-style name conflicts never happen,
- the shared registry can answer “is agent `<agent_id>` currently up?” directly from one live record keyed by `agent_id`,
- name-based live lookup becomes a convenience path layered on top of registry or manifest metadata and may need to surface ambiguity when more than one live agent shares the same canonical name,
- tmux session names can stay unique without forcing canonical agent name itself to be unique,
- the true canonical agent name for a running tmux-backed session is recovered from persisted manifest metadata or shared-registry publication rather than inferred from the tmux session name,
- whenever a Houmao-owned directory name must stand for one agent, `agent_id` is the directory-safe key and canonical agent name stays in metadata,
- future non-single-tool agents do not have to fit a tool-family directory taxonomy to participate in the same Houmao-owned layout.

Rationale:
- Operators need a strong, memorable name and generally expect the same name to refer to the same agent, much like a person's name in normal use, but the system should not pretend rare same-name conflicts are impossible.
- The system therefore needs an authoritative globally unique identifier for durable writable association and liveness checks.
- Bootstrapping the first `agent_id` from canonical agent name preserves the expected “same name, same agent” behavior for new agents without forcing users to mint IDs manually, while still allowing the persisted `agent_id` to survive later rename-like changes.
- Decoupling tmux session names from canonical agent names prevents accidental tmux auto-renaming from silently changing the operator-visible identity contract.
- Using metadata fields instead of directory buckets keeps the layout more future-proof than a taxonomy based on today's tool shapes.

Alternatives considered:
- *Use canonical agent name only and have no separate agent id* — rejected because it handles rare name conflicts and intentional rename cases poorly once writable state must be keyed globally.
- *Make `agent_id` the only meaningful identity and treat names as disposable labels* — rejected because operators still need a strong human-facing label for normal collaboration and lookup.
- *Keep recomputing `agent_id` from canonical agent name on every start* — rejected because that would make rename-like workflows silently create a different identity even when the operator intends to keep referring to the same agent.
- *Continue using canonical agent name as the tmux session name* — rejected because same-name conflicts are now allowed in principle and tmux collision renaming would make the session handle diverge from the intended agent identity anyway.
- *Make per-agent top-level directories the primary layout key* — rejected because the runtime still has multiple artifact classes with different lifecycles, and not all of them need to be physically nested under one per-agent root to remain associated.
- *Use tool family as the top-level grouping key* — rejected because it leaks an implementation property into the identity model.

### 5. Introduce a runtime-created per-agent job dir for destructive work

**Choice:** For every started session, create `<working-directory>/.houmao/jobs/<session-id>/` and expose it to the launched session as `AGENTSYS_JOB_DIR`.

This directory is intended for:
- session-local logs,
- temporary outputs,
- scratch files,
- work the agent may destructively rewrite or delete.

It is not the durable runtime session root and does not replace `manifest.json`, gateway state, or registry publication.

Rationale:
- The agent working directory should remain the main project context, but not every temporary or destructive artifact belongs at the project top level.
- A dedicated job dir gives agents a sanctioned place for “safe to trash” state.
- Putting it under the working directory keeps it adjacent to the actual project context that the agent is editing.

Alternatives considered:
- *Let every role or agent implementation invent its own scratch directory* — rejected because that produces inconsistent cleanup and unclear operator expectations.
- *Store scratch logs and outputs in the runtime session root* — rejected because the runtime session root is Houmao-controlled durable state, not an agent-destructive workspace.

### 6. Make the default mailbox root independent from the runtime root

**Choice:** Stop defaulting filesystem mailbox storage from the runtime root. When no explicit mailbox root is supplied, default to `~/.houmao/mailbox`.

Rationale:
- Mailbox is a shared asynchronous transport, not a child of one runtime session tree.
- The user explicitly wants mailbox to remain a separate writable area that multiple agents can share.
- This keeps mailbox lifecycle and cleanup independent from runtime/session cleanup.

Alternatives considered:
- *Keep defaulting mailbox under the runtime root* — rejected because it makes mailbox look like per-runtime or per-project scratch state even though it is logically shared state.
- *Place mailbox under the working directory* — rejected because mailbox is intentionally shared across agents and not scoped to one project workspace.

### 7. Treat this as a default-path migration, not as an in-place data migration

**Choice:** New starts/builds use the new defaults, but old manifests, explicit runtime-root overrides, explicit mailbox roots, and explicit launcher `home_dir` values continue to work as addressed paths.

Rationale:
- Existing manifests already persist absolute paths and can continue to resume from those locations.
- This keeps the change operationally simpler and avoids risky on-disk rewrites.
- Operators can move old roots manually if they want a clean filesystem, but correctness does not depend on it.

Alternatives considered:
- *Auto-migrate old runtime roots into `~/.houmao/runtime`* — rejected because it adds cross-filesystem copy/move risk and complicates rollback.
- *Refuse to resume old manifests until migrated* — rejected because it would turn a layout cleanup into a hard backward-compatibility break.

## Risks / Trade-offs

- [Risk] Default path changes will surprise existing scripts and docs that assume `tmp/agents-runtime`. -> Mitigation: keep explicit `--runtime-root` overrides, document the new defaults clearly, and preserve resume for old manifests.
- [Risk] Creating `.houmao/` under working directories may be unwelcome in some repos. -> Mitigation: keep the per-agent job dir narrowly scoped under `.houmao/jobs/<session-id>/`, document its purpose, and avoid moving durable runtime state there.
- [Risk] Job dirs may accumulate after many sessions. -> Mitigation: document cleanup expectations now and keep open the option for a later pruning or retention policy.
- [Risk] Launcher default CAO home under the runtime root changes filesystem expectations for operators who currently rely on ambient HOME. -> Mitigation: preserve explicit `home_dir` override support and keep the home-vs-workdir separation explicit.
- [Risk] Mailbox default relocation could surprise environments that relied on implicit runtime-root-derived mailbox placement. -> Mitigation: preserve explicit mailbox-root overrides, add an env-var override for CI/dynamic runs, and call out the default change as breaking.
- [Risk] Explicitly reusing one `agent_id` across unrelated agents can merge or corrupt writable association state. -> Mitigation: bootstrap the default `agent_id` from canonical agent name, persist both name and id in metadata, and warn when one `agent_id` is seen with a different canonical name.
- [Risk] Name-based lookup can become ambiguous when different agents share the same canonical name. -> Mitigation: make direct liveness lookup by `agent_id` primary, persist both `agent_id` and canonical agent name in manifest and registry metadata, and surface ambiguity instead of silently guessing.
- [Risk] Relying on tmux auto-renaming could desynchronize live-session handles from persisted metadata. -> Mitigation: choose and persist tmux session names explicitly as unique live-session handles and recover true agent identity from manifest or registry metadata rather than from the session name itself.
- [Risk] Multiple override channels can create precedence confusion. -> Mitigation: document one precedence order consistently: explicit CLI/config override first, env-var override second, built-in default last.

## Migration Plan

1. Add shared path-resolution helpers for the effective Houmao roots and the derived job dir, including env-var override support and one documented precedence order.
2. Replace registry-specific `agent_key` with authoritative `agent_id` in runtime-owned metadata and shared-registry publication, and define how initial `agent_id` bootstrap vs persisted-identity reuse works.
3. Change runtime build/start defaults to use the Houmao runtime root, persist canonical agent name plus authoritative `agent_id`, choose and persist tmux session names as unique live-session handles, and create the job dir for new sessions.
4. Update registry publication and lookup so direct liveness resolution by `agent_id` is primary while convenience lookup by canonical name comes from registry or manifest metadata and can surface ambiguity.
5. Update launcher artifact paths and launcher-default CAO `HOME` derivation to use the new per-server runtime subtree.
6. Change mailbox default root resolution to the independent Houmao mailbox root while preserving explicit overrides and env-var relocation.
7. Update docs, reference pages, and examples so registry, runtime, mailbox, tmux session-handle, job-dir, env-var override, and name-vs-`agent_id` boundaries are described consistently.
8. Keep resume/control path compatibility for already-created manifests and explicit old paths.

Rollback strategy:
- Restore the previous default roots in runtime, launcher, and mailbox resolution code.
- Keep explicit old or new paths usable as addressed paths.
- Do not attempt to delete or rewrite already-created `~/.houmao/runtime`, `~/.houmao/mailbox`, or `.houmao/jobs/` data automatically during rollback.

## Open Questions

- Should graceful `stop-session` eventually offer an optional cleanup mode for `<working-directory>/.houmao/jobs/<session-id>/`, or should cleanup remain entirely manual in this change?
- Should future work add a registry-owned CAO server discovery namespace that publishes pointer-style server records without storing mutable CAO home or launcher state there?
