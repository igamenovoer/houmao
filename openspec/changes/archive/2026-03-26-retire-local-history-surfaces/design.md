## Context

The current history story is split across two different local/serverless surfaces:

- `houmao-mgr agents history`, which projects either local TUI tracker history or persisted local headless turn artifacts into one generic managed-agent history payload.
- Gateway-owned `GET /v1/control/tui/history`, which was recently enabled for runtime-owned `local_interactive` sessions and is documented in local workflow notes as part of serverless TUI tracking validation.

That split has two problems.

First, the local CLI history surface is not authoritative for the cases where operators actually care about live posture. For local TUI sessions, the live tracked `state` view is the supported source of current posture, while the bounded history view is ephemeral and easy to misread as durable or authoritative. For headless sessions, the real durable inspection surface is already the managed `turn` contract rather than a generic history wrapper.

Second, the gateway history route is still coupled to the integrated server path. `houmao-server` consumes gateway and managed-agent history contracts today, so a full repo-wide history removal would require coordinated changes in the integrated CAO/server module. The user explicitly does not want that module touched in this change.

This design therefore treats history retirement as a scoped local/serverless cleanup rather than a global transport-contract removal.

## Goals / Non-Goals

**Goals:**

- Remove `houmao-mgr agents history` from the supported native CLI surface.
- Stop treating gateway TUI history as a supported local/serverless inspection path for runtime-owned `local_interactive` sessions.
- Keep local operator guidance centered on supported state-oriented surfaces:
  - `houmao-mgr agents state`
  - `houmao-mgr agents show`
  - `GET /v1/control/tui/state`
  - `POST /v1/control/tui/note-prompt`
  - managed headless `agents turn ...` inspection
- Preserve any history plumbing that the frozen integrated CAO/server path still consumes.

**Non-Goals:**

- Removing `GET /houmao/agents/{agent_ref}/history` from `houmao-server`.
- Removing `GET /houmao/terminals/{terminal_id}/history` from `houmao-server`.
- Removing gateway/shared-tracker history models or client methods that are still needed by the integrated server path.
- Changing managed-agent detailed-state models that still carry canonical history-route references for the integrated server/API surface.

## Decisions

### 1. Retire the native local history command instead of remapping it

`houmao-mgr agents history` will be removed rather than redirected to `state`, `show`, or another compatibility payload.

The rationale is that the command is semantically fuzzy:

- for TUI-backed local agents it exposes bounded tracker transitions that are not the primary supported inspection surface,
- for headless local agents it overlaps with the richer `agents turn ...` inspection path,
- and the combined managed-agent history wrapper makes these materially different retention models look more uniform than they are.

Removing the command makes the contract sharper instead of inventing another degraded compatibility layer.

**Alternatives considered:**

- Keep `agents history` and only fix its local TUI behavior. Rejected because the user no longer wants history endpoints as part of the local operator surface.
- Keep the command for headless-only sessions. Rejected because it preserves the generic history abstraction even though headless already has a better turn-oriented contract.

### 2. Narrow the runtime-owned local gateway tracking contract to current state plus explicit prompt-note evidence

For runtime-owned `local_interactive` sessions outside `houmao-server`, the supported local gateway tracking surface will be:

- `GET /v1/control/tui/state`
- `POST /v1/control/tui/note-prompt`

Prompt submission through `POST /v1/requests` will continue to feed explicit prompt-note evidence into the same tracker authority.

This keeps the local/serverless tracking contract focused on:

- current posture,
- explicit input provenance, and
- observable prompt lifecycle effects in current state,

without presenting bounded transition history as a required operator-facing surface.

**Alternatives considered:**

- Remove all gateway-owned TUI tracking for runtime-owned `local_interactive`. Rejected because current state and explicit prompt evidence are still useful and already align with the working local gateway path.
- Require history to remain because it exists in the gateway runtime already. Rejected because implementation existence is not a good reason to keep a public local contract the user does not want.

### 3. Preserve compatibility-only history plumbing that the integrated server path still depends on

This change will not modify the integrated CAO/server module. As a result, history-related plumbing that is still consumed by that path may remain in place even if it stops being a supported local/serverless operator surface.

Concretely, this means the design tolerates keeping some or all of the following in place for now:

- gateway history route handlers,
- gateway client history methods,
- shared tracker history methods,
- server-facing history response models.

The key point is contract ownership:

- local/serverless docs, help text, tests, and workflow guidance stop treating those surfaces as supported,
- integrated server/CAO behavior remains untouched in this change.

**Alternatives considered:**

- Fully remove all history plumbing immediately. Rejected because it would require integrated server changes that are explicitly out of scope.
- Leave the local history command and docs in place until the server path is ready. Rejected because the user wants the local/serverless retirement now.

### 4. Documentation and workflow examples should move from transition-history inspection to state-oriented inspection

Repo-owned docs and workflow notes will be updated so local/serverless validation focuses on:

- current tracked state,
- `last_turn` fields in that state,
- prompt-note provenance,
- and managed headless turn artifacts where applicable.

This is the operational consequence of the contract change. If the docs continue to teach `agents history` or `/v1/control/tui/history`, the code cleanup will not actually simplify operator expectations.

**Alternatives considered:**

- Leave docs untouched and rely on help output changes alone. Rejected because existing workflow notes would continue teaching retired surfaces.

## Risks / Trade-offs

- **Partial retirement leaves compatibility-looking code behind** → Document the boundary clearly in specs and tasks, and defer actual shared-plumbing removal to a later server-inclusive change.
- **Undocumented local history routes may still be callable directly** → Treat them as compatibility-only implementation detail rather than supported local workflow, and remove repo-owned docs/tests that endorse them.
- **Existing scripts using `houmao-mgr agents history` will break** → Make the removal explicit in help/specs/docs and point operators to `state`, `show`, and `agents turn ...` as the supported replacements.
- **Local tests may overfit the old workflow** → Update test coverage to validate the supported state-oriented path rather than reproducing retired history behavior.

## Migration Plan

1. Remove `houmao-mgr agents history` from the native CLI and delete the local managed-agent history wrapper that only exists to serve that command.
2. Narrow the runtime-owned local gateway tracking contract and repo-owned local workflow docs to `state` plus prompt-note behavior.
3. Update tests, workflow notes, and help-shape assertions so they no longer expect local history surfaces.
4. Leave integrated server/CAO history plumbing unchanged in this change.
5. Follow up later with a server-inclusive change if full repo-wide history retirement is still desired.

## Open Questions

- Should compatibility-only local gateway history code be marked explicitly as deprecated/internal in comments or docs, or is removing repo-owned usage enough for now?
- Once the integrated server path is allowed to change, do we want a second cleanup that removes history response models entirely, or only the TUI-tracking history surfaces?
