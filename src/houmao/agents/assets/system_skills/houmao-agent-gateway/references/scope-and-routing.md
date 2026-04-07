# Gateway Skill Scope And Routing

Use `houmao-agent-gateway` when the task is about the managed gateway itself or a live gateway-only service.

## Use This Skill For

- attach, detach, or inspect the live gateway
- manifest-first current-session gateway discovery
- gateway-owned prompt control, queued requests, raw key delivery, TUI inspection, or headless control
- direct live `/v1/wakeups`
- gateway mail-notifier control

## Use Other Houmao Skills For

- `houmao-manage-agent-instance`
  start, join, stop, relaunch, or clean up the managed agent session itself
- `houmao-agent-messaging`
  ordinary prompt, interrupt, or mailbox follow-up across already-running managed agents
- `houmao-agent-email-comms`
  the exact shared `/v1/mail/*` route contract once the exact live `gateway.base_url` is already known
- `houmao-process-emails-via-gateway`
  one notifier-driven unread-mail processing round
- `houmao-agent-email-comms`
  unified mailbox operations plus gateway-backed and no-gateway fallback detail

## Discovery Boundary

- Current-session managed identity is manifest-first: `HOUMAO_MANIFEST_PATH`, then `HOUMAO_AGENT_ID`.
- Live gateway env (`HOUMAO_AGENT_GATEWAY_HOST` and `HOUMAO_AGENT_GATEWAY_PORT`) is for live direct gateway control only.
- Exact live mailbox `gateway.base_url` should come from `houmao-mgr agents mail resolve-live` or the matching managed-agent HTTP resolver.
- `HOUMAO_GATEWAY_ATTACH_PATH` and `HOUMAO_GATEWAY_ROOT` are retired from the supported public discovery contract.
