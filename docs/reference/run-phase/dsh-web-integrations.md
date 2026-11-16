# DSH Web Gateway and Passive Observation

DSH interactive agents use `dsh_web`. The human browser and programmatic runtime address one explicitly bound native session in a Houmao-owned loopback Web Host. The tmux session supervises its process and logs. It does not provide a terminal agent interface.

Gateway publication identifies the Web origin, native session, managed generation, host incarnation, and native agent incarnation. Public metadata contains no connection token, signed URL, cookie, or provider credential. A browser navigating to another conversation does not change the managed target.

## Structured Inspection

The gateway exposes `GET /v1/control/web/state` and `GET /v1/control/web/history?limit=100`. State reports authenticated control availability, the native sequence/cursor, current and last native turn, pending inbox identities, human approval or question waits, live model selection, and sampled policy eligibility. History contains bounded native transition metadata with original execution identities. A receipt or input admission does not establish a terminal outcome or exclusive authorship of shared output.

Each state refresh also reads native pending interactions. A repeated state-stream cursor therefore does not hide a newly raised approval question. Sequence gaps require read-only history reconciliation. Missing, stale, revoked, or mismatched authority produces unavailable state and closes admission. It never becomes a remembered idle state.

The passive server selects Web observation from the declared backend/native surface. It creates no terminal parser for the supervisor pane. Its compact `/houmao/agents/{agent_ref}/state` response has a Web transport variant. `/state/detail` returns the canonical managed Web detail with shared identity, mailbox and gateway summaries, and the same structured Web state contract. `/history` returns bounded native transitions. The corresponding `/managed-state`, `/managed-state/detail`, and `/managed-history` routes remain available for common managed-agent clients.

A passive observer first tries a fresh gateway observation with the exact current binding. It can fall back to a verified direct native observation using private runtime authority. Both sources use the same state/detail contract and native transition identities. Inspection does not launch a Web Host, restore a cold agent, retarget a session, resend a prompt, or answer a human interaction.

## Admission and Shared Activity

Ordinary plugin events, CCCC chat deliveries, mailbox reminders, and scheduled prompt reminders use `ready_only`. Native insertion rechecks the deadline, caller lifetime, exact execution incarnation, true idle claim, pending inbox, and human interaction waits after asynchronous preparation. A browser request that wins this race closes ordinary admission. Refusal retains no gateway retry or native follow-up input for that delivery.

For Web agents, ordinary `POST /v1/requests` prompt calls also wait for native insertion acknowledgement. Their durable rows contain operation and execution metadata in `observing` state, with no executable prompt payload. Those rows never enter the gateway queue worker. A gateway restart marks unfinished observations failed or uncertain and performs no resend. Interrupt requests act immediately on the captured native turn instead of entering a delayed cancellation queue.

A completed gateway observation requires a successful native terminal result. Failed or interrupted native work and failed controller observation produce a failed operation row. Native receipts retain the actual outcome independently, including when controller publication fails after native completion.

Explicit operator `POST /v1/control/prompt` requests may select these policies:

| Policy | Native Admission |
| --- | --- |
| `ready_only` | Live, idle, unblocked agent with an empty inbox. |
| `if_no_pending` | Live, unblocked agent with an empty inbox; active work may continue before the explicitly queued input. |
| `always` | Exact structurally available execution; native readiness and inbox checks are bypassed for this requested insertion. |

The latter policies authorize an explicit native queue operation. They do not authorize delivery retries, cold activation, or substitution of another native body. Explicit `chat_session.mode=new` requires `ready_only` and uses guarded native lifecycle reset before binding the returned new conversation. `current` and an exact selector naming the currently bound native session preserve that binding; other selectors are refused. An insertion acknowledgement identifies admitted input; shared state and native terminal evidence establish its later outcome.

Mailbox wakeups preserve the configured offline/online transport and owner binding. Periodic reminders remain subject to fresh native admission on every delivery. Shared-session observation includes browser-origin work and model changes. AG-UI exposes Web activity snapshots with native identities; it does not invent terminal text or attribute all subsequent human activity to the waiting programmatic caller.

## Capability and Recovery Boundaries

Raw keys, terminal capture, terminal parser snapshots, terminal history, terminal tracking, and TUI timing options are unsupported for Web agents. Use semantic prompt/interrupt operations and the Web state/history routes. A healthy supervisor pane cannot replace unavailable native control.

Gateway detach leaves the owned host and browser session running. Managed stop shuts down the owned host. Attaching a gateway or reconnecting an observer preserves the existing binding. Explicit relaunch may restore the native conversation under new host/agent incarnations; old operations keep their original outcomes and are not replayed. Status, attach/detach publication, and passive refresh preserve newer manifest state written by another controller.

When a source reports unavailable, inspect the token-free origin and current binding, then use the supported explicit lifecycle or credential-reconnection operation. Reconciliation reads receipts/history without resending input. An uncertain admission remains uncertain until native metadata resolves it. The first release does not adopt manually launched Web Hosts or use browser automation for production control.
