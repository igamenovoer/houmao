## Context

Gateway mail-notifier behavior is currently configured as a small singleton state object owned by the live gateway and persisted in the gateway queue database. The direct gateway API, passive/server-managed proxy routes, CLI commands, and rendered notifier prompt all share that state, but today the state only covers enablement, polling interval, and notification mode.

This change adds runtime-specific user guidance that belongs to notifier-owned wake-up context rather than to the mailbox-processing skill contract. The appendix must therefore behave like notifier configuration: queryable through gateway status reads, modifiable through gateway writes, durable across notifier disable and re-enable within the same runtime session, and rendered only when present.

The user also wants this appendix to participate in birth-time launch defaults. That means the appendix must exist in two related forms:
- as live gateway notifier state controlled through `GET|PUT|DELETE /v1/mail-notifier`,
- as an optional shared launch-profile default authored through both the explicit and easy launch-profile lanes and materialized into the runtime-owned gateway notifier state for future launches.

## Goals / Non-Goals

**Goals:**
- Add notifier-owned `appendix_text` state that is queryable through direct gateway status and managed-agent gateway proxy status.
- Allow direct gateway and proxy `PUT` writes to replace `appendix_text` when provided, preserve it when omitted, and clear it when an empty string is provided.
- Preserve notifier disable semantics so `DELETE /v1/mail-notifier` stops polling without erasing appendix configuration.
- Append non-empty appendix text to rendered notifier prompts without changing the mailbox-processing skill contract.
- Expose the same appendix configuration through the native `houmao-mgr agents gateway mail-notifier` CLI.
- Extend the shared launch-profile model with an optional gateway mail-notifier appendix default.
- Expose that stored default through both `project agents launch-profiles` and `project easy profile` authoring surfaces.
- Seed launch-profile-owned notifier appendix defaults into runtime gateway notifier state during launch preparation.

**Non-Goals:**
- No arbitrary template override or template-fragment injection surface beyond one appended free-text block.
- No new notifier routes such as `/v1/mail-notifier/appendix`; appendix remains part of the existing singleton notifier state.
- No change to mailbox-processing skill workflow ownership, mailbox selection rules, queue-admission rules, or notifier busy gating.
- No new structured appendix schema such as Markdown sections, labels, or multiple appendix blocks.
- No stored launch-profile support for full mail-notifier enablement policy, interval, or mode in this change; the launch-profile concern is appendix default only.

## Decisions

1. Treat `appendix_text` as durable notifier state.

   The appendix belongs in the same gateway-owned notifier record as `enabled`, `interval_seconds`, and `mode`. This keeps direct gateway reads, proxy reads, CLI output, and prompt rendering aligned around one source of truth instead of introducing a second prompt-config store.

   Alternative considered: a separate appendix-only endpoint or file. Rejected because it would split a small singleton configuration surface across multiple contracts without adding meaningful flexibility.

2. Use simple string update semantics.

   `GET /v1/mail-notifier` always returns the effective `appendix_text`, defaulting to the empty string. `PUT /v1/mail-notifier` interprets appendix input as:
- omitted field -> preserve the stored appendix unchanged
- non-empty string -> replace with that string
- empty string -> clear the appendix

   This avoids a separate clear flag and matches the user’s intended control model.

   Alternative considered: explicit `appendix_update` or `clear_appendix` fields. Rejected because the extra control plane is unnecessary when empty string already provides a clean clear signal.

3. Preserve appendix state when disabling the notifier.

   `DELETE /v1/mail-notifier` remains a disable operation only. It does not erase `appendix_text`, so a later re-enable can reuse the same runtime-specific context unless the caller explicitly changes or clears it through `PUT`.

   Alternative considered: clear appendix on delete. Rejected because it couples polling control to configuration erasure and makes temporary disablement surprising.

4. Keep appendix rendering separate from mailbox workflow instructions.

   The gateway notifier prompt continues to own wake-up context only: mailbox-skill invocation, mode, gateway base URL, mailbox API summary, and optional appendix text. The appendix is rendered as an extra appended block only when non-empty. The mailbox-processing skill remains authoritative for round behavior such as selection, reply flow, archive timing, and stop-after-round discipline.

   Alternative considered: folding appendix text into the existing workflow sentence or using it to replace notifier instructions. Rejected because it weakens the boundary between notifier context and mailbox-processing behavior.

5. Preserve omitted-vs-provided semantics through model validation.

   The write path must distinguish an omitted appendix field from an explicitly supplied empty string. The gateway request model and proxy forwarding path should therefore preserve field presence, not just final normalized values, so the runtime can decide whether to keep the stored appendix or overwrite it.

   Alternative considered: normalizing missing and empty to the same value early in parsing. Rejected because it would make “preserve current appendix” impossible through `PUT`.

6. Store launch-profile appendix defaults in the shared launch-profile model and expose them through both lanes.

   The appendix default belongs with other birth-time launch defaults in the shared launch-profile object family. The explicit recipe-backed lane and the easy profile lane should both author the same underlying field so later launches behave consistently regardless of which lane created the profile.

   Alternative considered: making appendix defaults explicit-lane only. Rejected because the shared launch-profile model already spans both lanes and the user explicitly wants easy-profile coverage.

7. Use normal profile clear-flag semantics for stored profile edits.

   Live gateway API uses omitted/non-empty/empty-string semantics because it is already a singleton state update surface. Launch-profile CLI surfaces should follow the repo’s established stored-profile mutation pattern instead: set with `--gateway-mail-notifier-appendix-text <text>` and clear with `--clear-gateway-mail-notifier-appendix`.

   Alternative considered: using empty string as the profile-layer clear signal too. Rejected because profile `set` surfaces already prefer explicit clear flags for stored nullable fields, and matching that pattern keeps patch versus clear behavior easier to read.

8. Materialize launch-profile appendix defaults into runtime gateway notifier state at launch time, even while the notifier is disabled.

   The launch-profile appendix default should seed the runtime-owned gateway notifier state during launch preparation so later `mail-notifier enable` can reuse it automatically. This keeps the value inside the same runtime state object used by live gateway reads and writes, while preserving the rule that later live runtime edits do not rewrite the stored profile.

   Alternative considered: deriving the appendix from the launch profile only when the notifier is first enabled. Rejected because it would require the live gateway enable path to rediscover launch-profile metadata instead of reading its own runtime-owned state.

## Risks / Trade-offs

- [Presence-sensitive parsing can be implemented incorrectly] -> Use model- or payload-level field-presence tracking in the direct gateway and proxy path, and add tests for omitted, non-empty, and empty-string writes.
- [Prompt growth can make notifier wake-ups noisy] -> Keep appendix as one appended block, default empty, and document that it is runtime guidance rather than a second workflow contract.
- [SQLite schema update must not break existing runtimes] -> Add the new column with empty-string default and treat missing historical values as empty during read or migration.
- [CLI and proxy behavior can drift from direct gateway semantics] -> Reuse the same notifier request/status models and add tests that assert forwarding of both non-empty and empty appendix values.
- [Launch-profile and live runtime semantics can diverge] -> Keep one shared underlying appendix field for both profile lanes, seed it into runtime gateway state at launch, and test explicit-lane plus easy-lane launches.
- [Profile-layer clear semantics can be confused with live API clear semantics] -> Document that profile authoring uses an explicit clear flag while live gateway `PUT` uses empty string to clear.

## Migration Plan

1. Extend the gateway notifier persistence model with an `appendix_text` column that defaults to `''`.
2. Update direct gateway notifier request/status models and runtime logic to preserve omitted writes, replace on provided strings, and render non-empty appendix text.
3. Extend the shared launch-profile model plus explicit/easy profile authoring surfaces with a stored notifier appendix default.
4. Update launch/runtime materialization so profile-owned appendix defaults seed runtime gateway notifier state before later live notifier control.
5. Update managed-agent gateway proxy/client layers to forward and return the appendix field unchanged.
6. Update `houmao-mgr agents gateway mail-notifier` to set and display appendix text using the same semantics.
7. Update docs and tests across runtime, proxy, launch-profile, easy-profile, and CLI surfaces.

Rollback consists of removing the feature in code and ignoring the stored appendix column; legacy rows with the added column remain harmless because the value is additive prompt context only.

## Open Questions

None.
