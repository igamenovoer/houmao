# DSH Headless Integrations

The manager and passive server select `dsh_headless` for a DSH agent in `headless` mode. Each accepted turn uses the native one-shot CLI. [DSH headless launch](dsh-headless.md), [DSH Web](dsh-web.md).

## Gateway Control

An idle managed DSH envelope remains gateway-capable between turns. A native CLI worker runs for each explicitly submitted turn and exits after native settlement. Gateway attachment and inspection reconstruct existing control without creating another native conversation or replaying an earlier prompt.

Use `GET /v1/status`, `POST /v1/control/prompt`, and `GET /v1/control/headless/state` for semantic control and inspection. Headless prompt control accepts `ready_only`; `if_no_pending` and `always` remain unsupported. Exact continuation uses the saved native session. An explicit new conversation creates a new native binding while retaining previous usage history.

DSH headless exposes semantic controls and structured state. `POST /v1/control/send-keys` reports unsupported capability instead of writing into the supervisory tmux pane. Native interruption remains a semantic runtime operation.

Ordinary plugin events use the existing immediate dispatch port. A dispatch response requires this attempt's native handoff evidence. Busy work, expired caller authority, unavailable execution, or a changed generation refuses the attempt. Provider or controller failure never authorizes an automatic resend. A sender may initiate a new request after inspecting the failed or uncertain result.

## Passive-Server Authority

The maintained passive server accepts tool `dsh` at `POST /houmao/agents/headless/launches` and persists backend `dsh_headless`. Follow-up control uses the returned managed identity through these routes:

| Operation | Route |
| --- | --- |
| Submit one turn | `POST /houmao/agents/{agent_ref}/turns` |
| Inspect a turn | `GET /houmao/agents/{agent_ref}/turns/{turn_id}` |
| Read canonical events | `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` |
| Read raw provider JSON events | `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` |
| Interrupt active work | `POST /houmao/agents/{agent_ref}/interrupt` |
| Stop the managed envelope | `POST /houmao/agents/{agent_ref}/stop` |
| Read finalized usage | `GET /houmao/agents/{agent_ref}/usage` |

The events route returns canonical semantic records. The stdout artifact retains the native CLI JSON event stream. The display console renders canonical events.

After passive-server restart, reconstruction preserves the original active-turn identity. A surviving owned process stays active. Terminal artifacts clear its old admission marker without launching another worker. If the managed body disappears, durable turn and usage history remain queryable while control reports unavailable. Concurrent turn requests reserve at most one active worker.

## Mailbox and Owner-Bound Plugins

DSH retains its logical agent and independently selected offline/online mailbox bindings. Enabling a mailbox notifier does not select another transport, create another mailbox identity, or mark messages read. Unchanged eligible inbox work continues to generate reminders at the configured interval. Reminders use the current DSH conversation and ordinary semantic execution; busy execution defers the next poll under the existing notifier policy.

CCCC chat and explicit deferred-message consumption use their owner's plugin event port. Their service credentials, owner, binding, and native references remain scoped by the existing plugin contract. Ordinary CCCC offers receive immediate admission or refusal; refused content is not stored as a later Houmao delivery. Explicit deferred consumption remains an operator-selected service action and uses the same ordinary dispatch boundary when it wakes the agent.

## Evidence

The [maintained qualification runner](../../../scripts/qualification/dsh/README.md) exercises the native profile with selected routes. `tests/integration/agents/dsh/test_fixture_headless.py` qualifies raw and managed exact continuation against a controlled loopback provider. The [RC2 scenario map](dsh-headless-acceptance.md) documents the prior ACP integrations separately.
