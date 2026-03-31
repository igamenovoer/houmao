## Context

The current top-level `houmao-mgr mailbox ...` and repo-local `houmao-mgr project mailbox ...` surfaces both reuse `mailbox_support.py` to read message summaries from the shared mailbox root. That helper currently joins `mailbox_state` and emits `read`, `starred`, `archived`, and `deleted` in the returned payloads.

This is wrong in two ways. First, the implementation is stale: manager-owned read-state mutation and gateway-driven follow-up already update mailbox-local `message_state`, so the admin payload can disagree with the state visible through `houmao-mgr agents mail ...`. Second, even a fully synchronized implementation would still be conceptually ambiguous because those fields are participant-local mailbox view state, not canonical message facts.

The relevant operator distinction is:

- `houmao-mgr mailbox ...` and `houmao-mgr project mailbox ...` are root-oriented inspection and administration surfaces.
- `houmao-mgr agents mail ...` is the actor-scoped follow-up surface for one managed agent's mailbox view.

## Goals / Non-Goals

**Goals:**

- Remove ambiguous participant-local mutable view-state fields from mailbox admin and project mailbox message payloads.
- Preserve useful structural inspection data for one selected address, including canonical message identity and address-scoped projection metadata.
- Keep the top-level mailbox and project mailbox wrappers aligned on the same payload contract so operators do not get different semantics depending on entrypoint.
- Move workflow-completion verification language in docs and testcases onto actor-scoped mail surfaces such as `houmao-mgr agents mail ...`.

**Non-Goals:**

- Introduce a new address-scoped state-inspection command for filesystem mailboxes.
- Redesign mailbox storage or migrate existing mailbox-state tables.
- Change the actor-scoped semantics of `houmao-mgr agents mail check`, `status`, `reply`, or `mark-read`.

## Decisions

### Remove mutable mailbox-view fields from admin and project message payloads

`list_mailbox_messages()` and `get_mailbox_message()` will stop selecting and serializing `is_read`, `is_starred`, `is_archived`, and `is_deleted`. That shared helper already defines the payload contract for both `houmao-mgr mailbox messages ...` and `houmao-mgr project mailbox messages ...`, so removing the fields there keeps both surfaces aligned.

Alternative considered: switch these admin payloads to mailbox-local `message_state` so they report fresher values. Rejected because the result would still be participant-local state presented on an administrative mailbox-root surface, which preserves the conceptual ambiguity even if the immediate bug disappears.

### Keep address-scoped projection metadata such as `folder` and `projection_path`

The commands still accept an explicit mailbox address, so it remains useful and unambiguous to show how the selected canonical message projects into that address. Fields such as `folder`, `projection_path`, and `registration_id` describe address-scoped structural placement, not mutable participant sentiment or workflow progress.

Alternative considered: remove `folder` together with `read`. Rejected because `folder` is part of the projection shape operators need when inspecting mailbox indexing or delivery routing, and its meaning is tied to the explicit address parameter already present in the command.

### Treat actor-scoped mail commands as the supported state-reporting boundary

The design does not create a new mailbox-root state-reporting contract. Operators who need read or unread follow-up state should continue to use `houmao-mgr agents mail ...`, which already resolves one managed agent and exposes mailbox follow-up semantics for that actor.

This applies to verification guidance as well. End-to-end docs and testcases should treat mailbox admin or project mailbox commands as corroborating structural inspection only. Completion checks such as "the processed message is no longer actionable unread mail" belong on actor-scoped commands like `houmao-mgr agents mail check --unread-only`.

Alternative considered: add a new mailbox-root command that explicitly asks for per-address state. Rejected for this change because the immediate requirement is to stop ambiguous reporting, not to define a second participant-local state contract.

### Keep project mailbox wrappers explicitly aligned with the root-level structural contract

The repository already has a dedicated `houmao-mgr project mailbox` spec surface. This change should state explicitly that `project mailbox messages list|get` reuses the same structural-only contract as `houmao-mgr mailbox messages list|get` and must not reintroduce participant-local view-state fields just because the mailbox root is project-scoped.

Alternative considered: rely only on the umbrella native CLI spec. Rejected because the project wrapper is a first-class operator surface and the ambiguity has already leaked into project-scoped testcases and expectations.

## Risks / Trade-offs

- [Breaking JSON shape for existing consumers] -> Update tests and mailbox docs in the same change so downstream expectations move with the contract.
- [Operators lose a quick `read` flag on mailbox admin commands] -> Point readers to `houmao-mgr agents mail check` or a future explicitly address-scoped state surface when they need workflow state instead of structural inspection.
- [Historical shared-root `mailbox_state` data remains on disk] -> Leave storage untouched for now; the admin surfaces simply stop presenting those rows as authoritative output.

## Migration Plan

1. Remove mutable view-state fields from the shared mailbox-support payload builders.
2. Update tests for both root-level and project-local mailbox message commands.
3. Refresh mailbox docs and testcase narratives to clarify that admin and project mailbox inspection is structural, while read-state follow-up lives on actor-scoped mail commands.

No data migration is required because the change only removes ambiguous fields from CLI payloads.

## Open Questions

None for this proposal. A future change may add an explicitly address-scoped state-inspection command if operators need a non-agent-bound participant-local view.
