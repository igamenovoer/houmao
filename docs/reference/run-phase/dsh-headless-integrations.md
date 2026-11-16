# DSH Headless Integrations

This reference describes DSH ACP integration with the gateway, passive server, and existing messaging services. Read [DSH Headless Compatibility](dsh-headless.md) for configuration and native lifecycle boundaries. The [acceptance map](dsh-headless-acceptance.md) separates executed controlled-runtime evidence from remaining qualification.

## Gateway Control

An idle managed DSH envelope remains gateway-capable between turns. The native ACP worker runs for an explicitly submitted turn and exits after native closure. Gateway attachment and inspection reconstruct existing control without creating another native conversation or replaying an earlier prompt.

Use `GET /v1/status`, `POST /v1/control/prompt`, and `GET /v1/control/headless/state` for semantic control and inspection. Headless prompt control accepts `ready_only`; `if_no_pending` and `always` remain unsupported. Exact continuation uses the saved native session. An explicit new conversation creates a new native binding while retaining previous usage history.

DSH ACP has no raw-key or terminal-parser control surface. `POST /v1/control/send-keys` reports unsupported capability instead of writing into the supervisory tmux pane. Native interruption remains a semantic runtime operation.

Ordinary plugin events use the existing immediate dispatch port. A dispatch response requires this attempt's native handoff evidence or a correlated successful settlement. Starting a helper is insufficient. Busy work, expired caller authority, unavailable execution, or a changed generation refuses the attempt. Provider or controller failure never authorizes an automatic resend. A sender may initiate a new request after inspecting the failed or uncertain result.

## Passive-Server Authority

The maintained passive server accepts tool `dsh` at `POST /houmao/agents/headless/launches` and persists backend `dsh_acp`. Follow-up control uses the returned managed identity through these routes:

| Operation | Route |
| --- | --- |
| Submit one turn | `POST /houmao/agents/{agent_ref}/turns` |
| Inspect a turn | `GET /houmao/agents/{agent_ref}/turns/{turn_id}` |
| Read canonical events | `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` |
| Read raw provider frames | `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` |
| Interrupt active work | `POST /houmao/agents/{agent_ref}/interrupt` |
| Stop the managed envelope | `POST /houmao/agents/{agent_ref}/stop` |
| Read finalized usage | `GET /houmao/agents/{agent_ref}/usage` |

The events route returns canonical semantic records. The stdout artifact retains the separate ACP provider transcript; rendered console output does not replace either artifact.

After passive-server restart, reconstruction preserves the original active-turn identity. A surviving owned process stays active. Terminal artifacts clear its old admission marker without launching another worker. If the managed body disappears, durable turn and usage history remain queryable while control reports unavailable. Concurrent turn requests reserve at most one active worker.

## Mailbox and Owner-Bound Plugins

DSH retains the same logical agent and independently selected offline/online mailbox bindings. Enabling a mailbox notifier does not select another transport, create another mailbox identity, or mark messages read. Unchanged eligible inbox work continues to generate reminders at the configured interval. Reminders use the current DSH conversation and ordinary semantic execution; busy execution defers the next poll under the existing notifier policy.

CCCC chat and explicit deferred-message consumption use their owner's plugin event port. Their service credentials, owner, binding, and native references remain scoped by the existing plugin contract. Ordinary CCCC offers receive immediate admission or refusal; refused content is not stored as a later Houmao delivery. Explicit deferred consumption remains an operator-selected service action and uses the same ordinary dispatch boundary when it wakes the agent.

## Evidence

`tests/integration/agents/dsh/test_gateway_passive.py` runs the identified native DSH executable against a controlled Messages endpoint with synthetic credentials. It covers exact-session semantic continuation, provider/debug artifact separation, passive authority reconstruction and usage, owner-bound CCCC delivery, and repeated filesystem mailbox reminders. Every runtime tmux command targets an explicit private socket through the `isolated_tmux` fixture.

Hermetic tests in `test_gateway_support.py` cover DSH busy refusal, failure before handoff, dispatch expiry, generation replacement, provider loss, and periodic reminders. `test_gateway_manifest_preservation.py` runs stale-controller capability, status, attach, and detach checks for DSH. Passive-server DSH tests cover launch authority, concurrent admission, a surviving recovered attempt, and preserved terminal history after body loss. Existing CCCC plugin tests cover owner and binding rejection, deferred consumption, and refusal without replay.

These checks qualify local structured integration. They do not establish live DeepSeek or unconfigured self-hosted provider acceptance, interactive browser behavior, or remote deployment support.
