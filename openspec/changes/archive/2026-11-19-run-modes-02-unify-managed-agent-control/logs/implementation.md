# Implementation and Verification

## Review After Change 01

- Reuse launch plan schema 3, session manifest schema 6, managed registry schema 5, and executor locator schema 2. Current executor discovery already verifies the owner binding, mode, and backend. Admission now also verifies that the active registry generation points to the exact manifest before native control.
- The manager's existing direct prompt path bypassed gateway readiness and allocated a request ID after dispatch. The shared owner reservation gives both entrypoints one current-generation slot and assigns the request identity before native work. Manager access follows the saved OS execution binding. Protected HTTP remains subject to the enrolled gateway policy.
- Use the maintained passive backing contract for passive-owned headless work. Preserve both passive route families and link curated TUI detail to the actual raw canonical route. Keep public handoff free of native credentials and private authority.
- The live environment selected `self-hosted` and `Qwen/Qwen3.8-27B-FP8` at the configured loopback endpoint. Each fixture owns its recorded tmux socket, and the live verifier clears inherited tmux selectors.

## Early Evidence

- The revised OpenSpec artifacts passed strict validation.
- Focused capability and tracker tests passed 12 cases. The runtime and manager suite passed 142 cases with one old manager fixture excluded while it was being updated for the owner reservation.
- Passive state verification is recorded in the companion log in this directory.
- The affected full Pixi unit suite passed 4,834 tests with 14 skipped. The suite reported ten dependency deprecation warnings. AG-UI gateway end-to-end integration passed four cases. Ruff, strict mypy (508 Python source files), and the documentation build passed.

## Owner Admission and Request Evidence

- A manager prompt reserves the same owner-local request slot as protected gateway control. The slot is qualified by active registry generation and canonical manifest path. Reserved, handed-off, and unverified work stays attributable after the submitting process disappears. Confirmed terminal evidence can release a slot. An uncertain result alone cannot release it.
- Kimi headless direct gateway control initially reports a queued operation ID. The worker's bridge records child and parent birth identities before they can be used for interruption. The installed aarch64 Pixi Python omitted pidfd functions. The Linux libc binding supplies the same pinned process signal path. A missing or changed birth identity refuses interruption without signaling a replacement PID or pane.
- A controlled native DSH Web integration enrolled a real gateway admin key and raced an authenticated HTTP request against a separate manager process with no admin signer. One caller gained admission and the provider received one invocation.
- Gateway verification passed 222 focused cases across eight suites. The final native Web integration run passed five cases, including the real manager and authenticated gateway race. The runtime and gateway contract integration passed 12 cases. The local TUI reports handoff after the prompt's actual Enter command. Bootstrap Enter and a failed receipt write cannot acknowledge it.
- When gateway and direct mailbox authority are unavailable, manager `send`, `reply`, and `mark` can fall back to a TUI prompt. A verified local TUI rechecks terminal readiness and process identity through prompt handoff. Retained CAO REST uses its successful terminal submission event and releases the slot after a verified ready terminal result. Both paths report submission-only mailbox results. Five focused cases covered admission conflicts and handoff on both backends, including CAO settlement. The combined manager, owner admission, and dispatch suite passed 110 tests. Scoped Ruff and strict mypy passed.
- AG-UI verification used real gateway routing and synthetic headless native artifacts. The integration harness now publishes a matching current owner record. The run produced request-correlated text and graphics. TUI unit streams report terminal handoff and leave provider completion unconfirmed.
- The saved-route integration exercised restricted sudo and pinned SSH on the live DSH Web lane. After the fixture gateway exited, the manager read the same native owner directly, reported the gateway offline, stopped the owner, and relaunched it. The revived owner refused the retired generation. See [saved executor verification](routed-verification.md).

## Live Manager and Gateway Verification

| Lane | Result |
| --- | --- |
| Kimi `2.6.0`, `headless`, `kimi_headless`, OpenAI Chat | Passed. Enrolled admin, rejected unsigned prompt with HTTP 401, completed manager and signed gateway turns, admitted one of two racing callers, interrupted the exact headless worker, and observed the same mode after detach, reattach, stop, and relaunch. |
| Kimi `2.6.0`, `tui`, `local_interactive`, OpenAI Chat | Passed. Enrolled admin, rejected unsigned prompt with HTTP 401, observed exact answers after both direct manager and signed gateway handoff, admitted one of two racing callers, interrupted an active terminal turn, and retained the agent through detach, reattach, stop, and relaunch. |
| DSH `0.2.2-rc.3`, `web`, `dsh_web`, pi-ai OpenAI Chat | Passed. Enrolled admin, rejected unsigned prompt with HTTP 401, completed exact native operations through both surfaces, admitted one of two racing callers, interrupted the captured Web turn, and preserved owner identity and mode across gateway detach and lifecycle actions. |

All three lanes used `Qwen/Qwen3.8-27B-FP8`, fresh external fixture roots, and their recorded private tmux servers. Each stopped its owned test agent.

## Terminal Evidence and Usage

Native Kimi `2.6.0` ran the manager prompt and displayed the requested `OWNER_TUI` reply. Its wire log carried `usage.record`, `turn.ended`, and `prompt.completed`. Plain terminal submission had native user origin and an unrelated prompt identity. The usage collector correctly refused to attach that record to the managed operation ID. Removed the new manager-side TUI usage preregistration to retain native accounting for manager turns. Signed gateway TUI accounting retains its existing exact-association requirement.

An attached gateway initially held the Kimi turn open after the exact reply was visible. The terminal showed a stable empty composer and a sampled successful turn, while the Kimi hook channel still advertised an active epoch. The live control qualification reads the actual reply and bounded terminal state. It makes a provider completion claim only for modes with exact native correlation.

Kimi emits `Stop` conditionally after a model step. The subscriber for `TurnEnded` emits hooks for failure and cancellation. A completed turn can therefore lack a terminal hook. The tracker checks up to the newest 1 MiB of the private main-agent journal when the verified terminal reports an idle, empty composer. It reuses its result while the journal and hook epoch are unchanged. A matching `turn.ended` record in the owned workspace and session must follow the hook epoch's arming time. The operation's public receipt remains a terminal handoff. A later manager process retains uncertainty about an outstanding TUI attempt if it lacks a continuous tracker or exact usage record. Local inspection, interruption, and lifecycle remain available to the verified owner.

Hook and Kimi tracker verification passed 434 tests. The new case holds readiness through stale terminal evidence, child-agent records, partial writes, and a busy terminal. It releases the hook epoch when the exact completed record and ready terminal agree. The shared tracking, Codex merge, and provider-neutral hook tests passed another 74 tests. Scoped Ruff and strict mypy passed.

## Reproduce Unit and Fixture Checks

```bash
pixi run lint
pixi run typecheck
pixi run docs-build
openspec validate run-modes-02-unify-managed-agent-control --strict

unset TMUX TMUX_PANE
export TMUX_TMPDIR="$(mktemp -d /tmp/houmao-mode02-tests.XXXXXX)"
pixi run test

pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client kimi --mode tui --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144
```
