---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Gateway Skill Scope And Routing

Use `houmao-shared-routines->houmao-agent-gateway` when the task is about the managed gateway itself or a live gateway-only service.

## Use This Skill For

- attach, detach, or inspect the live gateway
- manifest-first current-session gateway discovery
- gateway-owned prompt control, queued requests, raw key delivery, TUI inspection, or headless control
- direct live `/v1/reminders`
- gateway mail-notifier control

## Use Other Houmao Skills For

- `houmao-shared-routines->houmao-agent-inspect`
  generic managed-agent liveness, mailbox posture, runtime artifacts, non-gateway logs, and tmux-backing inspection
- `houmao-shared-routines->houmao-agent-instance`
  start, join, stop, relaunch, or clean up the managed agent session itself
- `houmao-shared-routines->houmao-agent-messaging`
  ordinary prompt, interrupt, or mailbox routing across already-running managed agents
- `houmao-shared-routines->houmao-process-emails-via-gateway`
  one notifier-driven open-mail processing round
- `houmao-shared-routines->houmao-agent-email-comms`
  unified mailbox operations, the exact shared `/v1/mail/*` route contract, and gateway-backed or no-gateway fallback detail

## Discovery Boundary

- Current-session managed identity is manifest-first: `HOUMAO_MANIFEST_PATH`, then `HOUMAO_AGENT_ID`.
- Live gateway env (`HOUMAO_AGENT_GATEWAY_HOST` and `HOUMAO_AGENT_GATEWAY_PORT`) is for live direct gateway control only.
- Exact live mailbox `gateway.base_url` should come from `houmao-mgr agents self mail resolve-live`, `houmao-mgr agents single ... mail resolve-live`, or the matching managed-agent HTTP resolver.
- `HOUMAO_GATEWAY_ATTACH_PATH` and `HOUMAO_GATEWAY_ROOT` are retired from the supported public discovery contract.
