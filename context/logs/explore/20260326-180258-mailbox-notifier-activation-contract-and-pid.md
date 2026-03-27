# Explore Log: mailbox notifier activation contract and pid discussion

**Date:** 2026-03-26
**Topic:** Why manifest mailbox binding is not the same as live mailbox readiness, why pid is not a sufficient authority signal, and how the gateway mail-notifier contract should change
**Mode:** `openspec-explore`

## Short Answer

The issue is not that the gateway mail notifier cannot see unread mail. It can.

The issue is that the current notifier support contract is too weak. It treats "the manifest has a mailbox binding" as equivalent to "the live session is ready to act on notifier prompts." For `local_interactive`, that is false during the `pending_relaunch` phase after late mailbox registration.

The pid idea does not fix that.

- For `local_interactive`, a live pid only answers "some process is alive in or under this pane."
- It does not answer "the correct provider TUI is live."
- It also does not answer "the live session has current mailbox env bindings projected."

The runtime already models those as separate questions. The notifier contract currently ignores that separation.

## Live Evidence From The Real Run

We exercised the real operator path:

1. `houmao-mgr mailbox init --mailbox-root tmp/hacktest-mailbox-codex-gateway/root`
2. `houmao-mgr agents launch --agents mailbox-demo --provider codex --agent-name htt-mailbox-codex --session-name hm-htt-mbox-codex --yolo`
3. `houmao-mgr agents mailbox register --agent-name htt-mailbox-codex --mailbox-root ...`
4. `houmao-mgr agents gateway attach --agent-name htt-mailbox-codex`
5. `PUT /v1/mail-notifier`
6. deliver one real unread filesystem mailbox message

Observed behavior before relaunch:

- `agents mailbox register` succeeded and persisted a real filesystem binding.
- `agents mailbox status` reported `activation_state=pending_relaunch`, `registered=true`, `runtime_mailbox_enabled=false`.
- the live gateway attached successfully and exposed `/v1/mail-notifier` and `/v1/mail/*`
- the gateway notifier detected unread mail and enqueued a real notifier request
- the Codex pane visibly received the notifier prompt
- the Codex pane then showed that mailbox env bindings were absent, so the prompt was not readily actionable on the live provider surface

Observed behavior after relaunch:

- `houmao-mgr agents relaunch --agent-name htt-mailbox-codex` succeeded
- `agents mailbox status` changed to `activation_state=active`, `runtime_mailbox_enabled=true`
- tmux session env now published the expected `AGENTSYS_MAILBOX_*` bindings
- a second unread message triggered another notifier enqueue and another visible prompt in the live Codex pane
- this time the Codex session could see mailbox bindings and started using them
- within the observation window, the message still remained unread, so the run proved notification delivery and improved live readiness, not full autonomous follow-through

This means the notifier path is real and functioning, but the advertised readiness level before relaunch is misleading for local interactive sessions.

## The Current Contract Split

The system already contains two different concepts, but the gateway notifier exposes only one of them.

```text
MAILBOX STATE MODEL

no binding
  |
  | late register
  v
persisted mailbox binding exists
manifest knows mailbox identity
transport state is real
live provider may still be stale
activation_state = pending_relaunch
  |
  | relaunch
  v
live mailbox binding is active
manifest + live env + provider surface agree
activation_state = active
```

The runtime and CLI respect that split:

- `RuntimeSessionController.mailbox_activation_state()` returns `pending_relaunch` for `local_interactive` after late mailbox mutation until live state catches up.
- `houmao-mgr agents mail ...` rejects use during `pending_relaunch`.

The gateway notifier does not respect that split:

- notifier support is currently derived by "can I load mailbox config from manifest and build an adapter?"
- that treats persisted transport truth as sufficient for notifier readiness
- the notifier prompt itself then assumes the live session can consume runtime-owned mailbox skills and mailbox env bindings

That is the mismatch.

## Why Pid Is Not The Right Fix

The question was: the manifest has a pid there, why not just use that to decide if the agent is there?

There are three separate reasons.

### 1. For `local_interactive`, pid is not the primary readiness contract today

`local_interactive` persists backend state through the inherited tmux-backed headless serializer, which does not include a dedicated provider pid. `runtime.agent_pid` is only populated when a backend actually exposes a `pid` field through backend state. The `local_interactive` path does not naturally do that.

So even before arguing semantics, the contract is weak: for the backend we care about, manifest pid is not the stable, typed authority for provider readiness.

### 2. A live pane pid does not mean the provider TUI is live

The `local_interactive` pane deliberately falls back to an interactive shell after the tool exits:

```text
provider command
status=$?
print exit note
exec "$SHELL" -l
```

That means "there is a live pid in the pane tree" can mean:

- Codex is really running
- Codex exited and only the fallback shell is alive
- the pane was respawned and some wrapper process is alive

The runtime already knows this. Startup readiness does not trust pane existence or pane pid alone. It inspects the pane's descendant process tree and looks for the expected tool process by name.

### 3. Provider liveness is still not mailbox readiness

Even if we had a reliable provider pid, that would still only answer:

```text
is the provider process alive?
```

The notifier problem needs a stronger answer:

```text
is the live provider surface on the current mailbox bindings?
```

The pre-relaunch live run proved the distinction:

- provider was alive enough to receive the notifier prompt
- provider was not mailbox-ready enough to act on it cleanly because mailbox env bindings were still absent

Pid cannot detect that semantic mismatch.

## The Actual Design Flaw

The gateway notifier support contract currently conflates two layers:

1. transport-backed mailbox capability
2. live-session mailbox actionability

For direct gateway mailbox routes like `GET /v1/mail/check`, that may be acceptable. The gateway can read transport truth from the manifest-backed mailbox config and transport adapter.

For notifier prompts, it is not enough.

Notifier prompts are not just transport reads. They are delegated work handed to the live provider session. That means notifier readiness should be gated by live mailbox activation, not by manifest mailbox existence alone.

## Concrete Contract Problems

### 1. `GatewayMailNotifierStatusV1` cannot represent the degraded intermediate state

Today the model has:

- `supported: bool`
- `support_error: str | None`

That is too coarse.

It cannot express:

- mailbox binding exists
- unread transport reads are possible
- live provider session is not yet mailbox-actionable
- relaunch is required before notifier prompts are semantically safe

### 2. Gateway docs overstate what support means

Current gateway docs say notifier support is determined by manifest mailbox binding. That matches the code, but it overstates real end-to-end readiness for `local_interactive`.

### 3. Mailbox docs warn about `pending_relaunch`, but only for `agents mail ...`

The mailbox quickstart explicitly warns that local interactive late registration may require relaunch before treating runtime-owned mail commands as active.

That warning is directionally correct, but it stops at `agents mail ...` and does not extend the same caution to gateway notifier behavior.

### 4. Tests miss the important state

Existing notifier tests validate:

- no binding -> unsupported
- manifest binding exists -> supported
- unread polling and dedup behavior

What they do not validate is:

- local interactive session
- late registration
- `pending_relaunch`
- live gateway attached before relaunch
- notifier status or enablement under that state

That missing test coverage is why the contract drift was easy to miss.

## Current State In ASCII

```text
CURRENT GATEWAY NOTIFIER CONTRACT

manifest mailbox binding exists?
  |
  +-- no  -> supported = false
  |
  +-- yes -> supported = true


ACTUAL LIVE SEMANTICS FOR local_interactive

manifest mailbox binding exists?
  |
  +-- no  -> not supported
  |
  +-- yes
         |
         +-- activation_state = pending_relaunch
         |      transport reads work
         |      notifier prompt can be delivered
         |      live provider may still lack mailbox env bindings
         |
         +-- activation_state = active
                transport reads work
                notifier prompt can be delivered
                live provider mailbox contract is coherent
```

The code models the second tree. The notifier API currently exposes only the first tree.

## Proposed Solution

### Recommended path: make notifier readiness activation-aware

This is the smallest coherent fix.

#### Core idea

Keep transport-backed mailbox facade and notifier readiness as distinct concepts.

- `/v1/mail/*` may remain available when transport-backed mailbox config is usable
- `/v1/mail-notifier` should reflect whether notifier prompts are semantically safe for the live provider surface

#### Contract change

Extend notifier status with activation-aware state, reusing the runtime concept instead of inventing a new parallel one.

Possible shape:

```json
{
  "schema_version": 1,
  "enabled": false,
  "interval_seconds": null,
  "supported": false,
  "support_error": "Mailbox binding exists but live session remains pending relaunch.",
  "activation_state": "pending_relaunch",
  "relaunch_required": true,
  "last_poll_at_utc": null,
  "last_notification_at_utc": null,
  "last_error": null
}
```

#### Behavioral change

For `local_interactive` with late mailbox registration:

- `GET /v1/mail-notifier` should report the degraded state explicitly
- `PUT /v1/mail-notifier` should fail while `activation_state != active`
- pair and CLI notifier surfaces should relay the same state and failure reason

For already active sessions:

- notifier behavior remains unchanged

#### Why this is the right abstraction

It matches the runtime's actual mental model:

- persisted mailbox config is one thing
- live mailbox activation is another thing

And it keeps the notifier API honest: it no longer advertises success for a state that the runtime itself treats as not yet ready for runtime-owned mailbox work.

### Alternative path: make notifier prompts self-contained before relaunch

A more ambitious alternative would be:

- allow notifier enablement during `pending_relaunch`
- rewrite the notifier prompt so it carries all mailbox and gateway access details needed to act safely even without live projected mailbox env vars

This is possible, but it is a different product decision.

It effectively creates a second, gateway-driven mailbox execution contract that partially bypasses the normal live-session mailbox projection seam. That is a broader design change and should be its own change, not a quiet patch inside notifier CLI work.

### Recommendation

Do the activation-aware fix first.

Treat "pre-relaunch notifier prompts are fully actionable" as a separate future design only if you explicitly want that behavior.

## Relation To The Active OpenSpec Change

There is already an in-progress change:

- `openspec/changes/add-gateway-sendkeys-and-notifier-cli/`

That change is currently scoped as if notifier CLI exposure is mostly a route-and-targeting problem.

Based on the live run, it should also account for notifier activation semantics:

- clarify that notifier status must reflect live mailbox readiness, not just manifest mailbox binding
- add tests for the `pending_relaunch` local interactive case
- update docs so notifier control and mailbox late-registration semantics do not contradict each other

## Proposed OpenSpec Adjustment

If this is captured in OpenSpec, the active change should add a design decision like:

- mail-notifier support is activation-aware for local interactive late-bound mailbox sessions
- notifier enablement requires live mailbox activation, not only persisted manifest mailbox binding

And tasks like:

- add notifier status fields or equivalent contract for activation state
- add tests for late registration + gateway attach + pending relaunch + notifier rejection
- update gateway and mailbox docs to state the relaunch requirement consistently

## Exact Code And Doc Hotspots

Runtime activation model:

- `src/houmao/agents/realm_controller/runtime.py`
  - `RuntimeSessionController.mailbox_activation_state()`
  - `_apply_mailbox_live_state_after_mutation()`
  - `_mailbox_mutation_activation_state()`

CLI mailbox gating:

- `src/houmao/srv_ctrl/commands/managed_agents.py`
  - `mailbox_status()`
  - `mail_status()`
  - `_run_local_mail_prompt()`

Gateway notifier support:

- `src/houmao/agents/realm_controller/gateway_service.py`
  - `put_mail_notifier()`
  - `_notifier_support_status()`
  - `_mailbox_adapter_locked()`
  - `_build_mail_notifier_prompt()`

Notifier status model:

- `src/houmao/agents/realm_controller/gateway_models.py`
  - `GatewayMailNotifierStatusV1`

Docs that currently diverge:

- `docs/reference/mailbox/quickstart.md`
- `docs/reference/gateway/contracts/protocol-and-state.md`
- `docs/reference/gateway/operations/mailbox-facade.md`

Tests that likely need new coverage:

- `tests/unit/agents/realm_controller/test_gateway_support.py`
- `tests/integration/agents/realm_controller/test_gateway_runtime_contract.py`

## Final Position

The pid question points at a useful instinct, but it is aimed at the wrong layer.

The system does not primarily suffer from not knowing whether "a process exists." It suffers from not exposing the right readiness boundary between:

- persisted mailbox capability
- live mailbox activation
- notifier prompt actionability

The durable fix is to make notifier support activation-aware, not pid-aware.

## Revised Conclusion After Clarifying The Tmux-Container Assumption

The exploration above captured the conservative fix under the earlier assumption that the live provider process itself had to own the current mailbox env snapshot.

After clarifying the intended runtime model, the stronger conclusion is:

- the manifest should remain the durable mailbox authority,
- the owning tmux session environment should become the authoritative live mailbox projection for active managed sessions,
- runtime-owned mailbox work should resolve current mailbox bindings from that tmux-backed live projection through a runtime-owned helper boundary,
- inherited provider process env should be treated as a launch-time snapshot, not as the only authoritative live mailbox source after late mutation.

Under that design assumption, the real root cause is not merely "notifier status ignores activation state." The deeper problem is that mailbox actionability is still coupled to stale launch-time process env even though the runtime already has a mutable tmux-contained control plane.

That changes the preferred fix.

### Updated preferred fix

1. Keep `launch_plan.mailbox` in the manifest as the durable mailbox capability record.
2. Refresh the targeted `AGENTSYS_MAILBOX_*` keys in the owning tmux session environment whenever late mailbox mutation changes the effective mailbox binding.
3. Add one runtime-owned live mailbox binding resolver that reads only the targeted mailbox keys from the owning tmux session and returns a normalized current binding.
4. Update projected mailbox skills and runtime-owned mailbox prompts to use that resolver instead of assuming inherited process env is current.
5. Update gateway notifier readiness so it uses:
   - durable mailbox capability from the manifest
   - live mailbox actionability from the tmux-backed mailbox projection
6. Preserve explicit unsupported errors only for sessions where Houmao cannot safely update both durable mailbox state and tmux live projection.

### Why this is the better fit

It aligns with the repository's stated direction:

- managed agents are expected to live inside tmux sessions,
- tmux acts as the runtime container that holds mutable session env state,
- future managed backends such as `codex_app_server` are expected to adopt that same tmux-contained model,
- mailbox behavior should therefore follow the tmux container boundary instead of the provider process boundary.

It also keeps the abstractions clean:

- the manifest remains durable, secret-free where needed, and suitable for resume and gateway construction,
- tmux session env becomes live mutable runtime state,
- the agent is not asked to parse raw manifest JSON or scrape all tmux env ad hoc,
- a runtime-owned helper can keep tmux integration details out of prompt contracts.

### Stalwart implication

This clarified direction does **not** argue for dropping mailbox state from the manifest.

For `stalwart`, the manifest still needs to retain durable, secret-free mailbox metadata such as `credential_ref`, while the tmux live projection can carry the current session-local credential file path once it has been materialized for that session.

So the durable/live split should be:

- manifest = durable mailbox capability and transport-safe metadata
- tmux session env = current actionable mailbox projection for the active session

### OpenSpec outcome

Based on this clarified conclusion, the right follow-on change is no longer "activation-aware notifier only."

The better change is:

- define tmux-backed live mailbox binding resolution as the runtime contract for active managed sessions,
- update mailbox skills, mailbox prompts, and notifier readiness to use that contract,
- then let notifier support be activation-aware in terms of live tmux mailbox actionability rather than relaunch-based process-env freshness.

That is the rationale behind the new proposed OpenSpec change:

- `openspec/changes/use-tmux-live-mailbox-bindings/`
