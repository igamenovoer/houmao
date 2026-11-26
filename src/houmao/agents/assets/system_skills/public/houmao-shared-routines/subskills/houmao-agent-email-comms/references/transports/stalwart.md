---
metadata:
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

# Stalwart Online Mail

Use this reference when operating on an attached `online` mailbox slot backed by `stalwart`.

## Online Channel Operation and JMAP Readiness

- **Scoped CLI and gateway facade**: use `houmao-mgr agents self mail <verb> --channel online --expected-binding-id <binding_id>` (or `/v1/mail/online/...` against a live gateway). Houmao owns JMAP session access internally, so ordinary mail needs no raw password, management token, or hand-crafted JMAP HTTP call.
- **Intranet JMAP discovery and origin trust**: Stalwart online bindings resolve `/.well-known/jmap` (from `--base-url` or exact `--jmap-url`), enforce approved scheme/host/port origins (`--trust-jmap-origin` when intranet HTTP or custom ports are used), and require ready `Inbox`, `Sent`, and `Archive` JMAP mailbox roles. If an `online` slot is detached, unready, or needs `--trust-jmap-origin` / `reconnect` / `refresh`, route binding administration to `houmao-shared-routines->houmao-mailbox-mgr->agent-binding-online()`.
- **Channel isolation and `post` boundary**: an agent can hold independent `offline` and `online` bindings simultaneously; `canonical_mail_identity` never selects the channel, `online` errors never authorize falling back to `offline`, and operator-origin `post` remains unsupported on Stalwart.
- **Pagination, completeness, and compact receipts**: inspect bounded metadata pages (`limit: 50`, max `200`, no `include_body`), check `content_complete` on `peek`/`read`, verify `send`/`reply` via top-level `message_ref` + optional `peek` on the same `expected_binding_id`, and archive only after work and required replies succeed.
