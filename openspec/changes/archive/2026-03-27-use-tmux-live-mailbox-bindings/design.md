## Context

Late mailbox registration currently mutates the session manifest and launch plan, and for tmux-backed sessions it can also republish mailbox env vars into tmux session environment. That is enough for durable state, later resume, and transport-backed gateway inspection, but it is not enough for a long-lived provider process that inherited its process env earlier and never refreshes it.

The live run against a real `local_interactive` Codex session showed the failure clearly: after late filesystem mailbox registration, the gateway could see unread mail and deliver notifier prompts, but the provider surface still lacked current `AGENTSYS_MAILBOX_*` bindings until relaunch. The result was a misleading intermediate state where mailbox transport truth existed, but live mailbox actionability lagged behind.

The repository is converging on a stronger runtime assumption: managed agents run inside tmux-backed runtime containers, and tmux session environment is the mutable live control plane for those containers. Existing tmux-backed backends already publish discovery pointers such as `AGENTSYS_MANIFEST_PATH` there, and future managed backends such as `codex_app_server` are intended to adopt the same tmux-contained model. This change should therefore align mailbox behavior with that container boundary instead of continuing to treat launch-time process env as the only live source.

At the same time, the manifest remains necessary. It is the durable mailbox capability record used by resume, gateway adapter construction, registry publication, and secret-free transport metadata such as Stalwart `credential_ref`. The design therefore needs to separate durable mailbox authority from live mailbox projection rather than replacing one with the other.

## Goals / Non-Goals

**Goals:**
- Make late mailbox mutation actionable for tmux-backed managed sessions without requiring provider relaunch solely to refresh mailbox bindings.
- Define one consistent live mailbox binding authority for runtime-owned mailbox prompts, projected mailbox skills, and gateway notifier readiness.
- Preserve the manifest as the durable mailbox capability record for resume, registry, gateway construction, and secret-free transport metadata.
- Keep the live-binding path transport-aware so filesystem and Stalwart sessions can both reuse it when their tmux-published live bindings are complete.
- Encode the tmux-container assumption directly in the mailbox contract so future tmux-backed managed backends can adopt the same behavior.

**Non-Goals:**
- Removing mailbox binding persistence from the session manifest.
- Making arbitrary runtime env vars hot-swappable for every feature beyond mailbox-related work.
- Requiring agents to parse raw manifest JSON or enumerate unrelated tmux session env vars manually.
- Reworking filesystem mailbox registration lifecycle semantics such as `safe`, `force`, `stash`, `deactivate`, or `purge`.
- Defining a new non-tmux live-binding contract for backends that do not yet participate in the tmux container model.

## Decisions

### Decision: Split durable mailbox authority from live mailbox projection

The manifest remains the durable mailbox capability record. It continues to carry the transport, mailbox identity, transport-safe binding metadata, and Stalwart `credential_ref` needed for resume and gateway adapter construction.

Tmux session env becomes the authoritative live mailbox projection for active tmux-backed sessions. Subsequent mailbox work for those sessions should use the current tmux-published mailbox bindings rather than trusting the provider process's launch-time env snapshot.

This yields one clean model:

- manifest = durable mailbox truth
- tmux session env = live mutable mailbox projection
- inherited process env = convenience snapshot that may become stale after late mutation

Alternative considered:
- Make the manifest the only live mailbox source for agents.
  Rejected because asking mailbox skills or notifier prompts to parse raw manifest payloads directly is a poor agent contract, leaks internal manifest structure into prompt surfaces, and does not solve transport-local live materialization concerns such as Stalwart session credential files.

### Decision: Introduce a runtime-owned live mailbox binding resolver

Mailbox skills, runtime-owned mailbox prompts, and notifier prompts should not scrape tmux state ad hoc. Instead, the runtime should provide one normalized live mailbox binding resolver for tmux-contained sessions.

That resolver should:

- read only the targeted common and transport-specific mailbox env vars from the owning tmux session,
- validate that the live binding is coherent for the manifest-selected transport,
- return a normalized binding payload plus `bindings_version` and live source metadata,
- fall back to manifest-backed durable state only where live tmux projection is intentionally unavailable or incomplete,
- avoid exposing raw tmux integration details as the primary agent contract.

Projected mailbox skills can then instruct the agent to resolve current mailbox bindings through this runtime-owned helper before direct mailbox work, rather than telling the agent to assume that inherited `AGENTSYS_MAILBOX_*` process env values are current.

Alternative considered:
- Teach the agent to list all tmux env vars and parse the mailbox subset itself.
  Rejected because it makes tmux internals the prompt contract, broadens the surfaced state unnecessarily, and invites prompt-level drift around which variables are authoritative.

### Decision: Treat late mailbox mutation as complete when live tmux projection is refreshed safely

For tmux-backed managed sessions that the runtime controls, late mailbox registration or unregistration should update both:

- the durable manifest/launch-plan mailbox record, and
- the targeted mailbox projection in tmux session env.

Once that live tmux projection is refreshed successfully, subsequent runtime-owned mailbox work should be considered active without relaunch. The old `pending_relaunch` posture exists only because the live provider surface previously had no authoritative live mailbox refresh path.

This does not mean every runtime feature becomes hot-swappable. It means mailbox-related work uses the tmux-container live binding projection rather than relying on provider process env snapshots.

Sessions that lack the required managed authority to update both durable state and tmux session env remain unsupported rather than silently degrading into stale behavior.

Alternative considered:
- Keep `pending_relaunch` for interactive sessions and only tighten notifier readiness.
  Rejected because it fixes the symptom for notifier enablement but leaves the underlying live mailbox binding contract incoherent for all subsequent mailbox actions.

### Decision: Gateway notifier support combines durable mailbox presence with live mailbox actionability

Gateway notifier support should no longer mean only "the manifest has a mailbox binding." For tmux-backed sessions it should mean:

- the manifest exposes durable mailbox capability,
- the current tmux live mailbox projection is available and coherent for that transport,
- any transport-local live prerequisites are already materialized.

For filesystem transport, this means the tmux-published filesystem mailbox bindings are present and version-aligned with the current binding. For Stalwart, it also means the session-local credential file pointer in the live projection is present and valid.

The gateway keeps using the manifest as the durable mailbox capability source. It does not create a second persisted mailbox store. But notifier readiness and enablement must additionally respect live mailbox actionability.

Alternative considered:
- Keep manifest-only readiness and try to make notifier prompts self-heal through extra instructions.
  Rejected because notifier prompts should not carry the burden of compensating for a stale live mailbox contract.

### Decision: Keep tmux session env mailbox vars targeted and versioned

The live projection should continue using the existing mailbox env naming scheme:

- common `AGENTSYS_MAILBOX_*`
- transport-specific `AGENTSYS_MAILBOX_FS_*` or `AGENTSYS_MAILBOX_EMAIL_*`

The runtime should update or unset only the targeted mailbox keys in tmux session env. `AGENTSYS_MAILBOX_BINDINGS_VERSION` remains the change detector for subsequent mailbox work, and direct process env may continue to exist as a compatibility snapshot for launch-time consumers.

This keeps the live projection small, explicit, and compatible with current mailbox contracts instead of inventing a second mailbox key namespace just for tmux live refresh.

Alternative considered:
- Add a separate tmux-only mailbox namespace.
  Rejected because it creates two parallel binding contracts for the same data and forces skills, runtime prompts, and gateway logic to reconcile them.

### Decision: Preserve Stalwart's secret-free manifest and session-local credential materialization model

This change should not simplify Stalwart by removing manifest state. The durable manifest still needs to carry transport-safe metadata such as `credential_ref`, and the runtime still needs to materialize the session-local credential file before publishing a usable live mailbox projection.

The live resolver for Stalwart should therefore use:

- manifest-backed durable transport metadata, and
- tmux-published live `AGENTSYS_MAILBOX_EMAIL_*` values, including the current session-local credential file path

That keeps the secret-free durable model intact while still allowing late mailbox mutation or live binding refresh to become actionable without relaunch once the runtime has materialized the required per-session asset.

Alternative considered:
- Drop manifest mailbox persistence to simplify the Stalwart path.
  Rejected because tmux session env is live state, not durable state, and cannot replace the manifest's role in resume, gateway adapter construction, or secret-free credential reference storage.

## Risks / Trade-offs

- [Tmux live projection and manifest can drift] → Treat tmux env as a runtime-owned projection derived from durable manifest state, update them together inside mailbox mutation flows, and use `AGENTSYS_MAILBOX_BINDINGS_VERSION` plus validation to detect mismatches.
- [Mailbox skills become dependent on a new helper path] → Keep the live resolver runtime-owned, versioned, and small; fail explicitly when it cannot resolve a coherent live binding rather than silently falling back to stale process env.
- [Stalwart live binding can point at stale session-local credential files] → Materialize or validate session-local credential material before publishing the live projection and have the resolver verify the file exists before treating the binding as actionable.
- [Joined or partially managed sessions may not have safe live refresh authority] → Preserve explicit unsupported error paths when the runtime cannot safely update both durable mailbox state and tmux live projection.
- [Future backends might diverge from the tmux-container assumption] → Treat tmux-contained managed sessions as the normative mailbox live-binding contract and require future managed backends to conform when they join that runtime model.

## Migration Plan

1. Add the runtime-owned live mailbox binding resolver and the tmux mailbox projection refresh helpers.
2. Update mailbox mutation flows so tmux-backed sessions refresh or clear targeted mailbox vars in tmux session env alongside manifest updates.
3. Update runtime-owned mailbox prompts and projected mailbox skill assets to use the live resolver before direct mailbox work.
4. Update gateway notifier readiness and enablement to require live mailbox actionability in addition to manifest mailbox presence.
5. Revise late-mailbox tests, gateway notifier tests, and real-session integration coverage so tmux-backed late registration becomes usable without relaunch.
6. Update mailbox and gateway docs to describe manifest as durable mailbox authority and tmux session env as live mailbox projection.

Rollback is straightforward: revert the live resolver and tmux live-projection gating, and restore the previous relaunch-based mailbox activation model for interactive sessions.

## Open Questions

- Should notifier status expose explicit live-binding source metadata such as `live_source=tmux_session_env`, or is `supported` plus a clearer `support_error` enough?
- Should direct runtime-owned `agents mail ...` flows and projected mailbox skills use exactly the same resolver output schema, or should prompts receive a reduced normalized subset?
- When `codex_app_server` becomes tmux-contained, should it adopt the identical mailbox live-projection contract immediately or behind its own short transition flag?
