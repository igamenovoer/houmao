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

# Offline Filesystem Mail

Use this page for the selected offline binding, whose transport is `filesystem` locally or `registry` remotely. The registry host owns the filesystem store and durable membership. Agent hosts may have disjoint filesystems; registration never implies that a remote store path is locally readable.

Use the ordinary action pages against `/v1/mail/offline/...` at the exact gateway URL. When no gateway is attached, use `houmao-mgr agents self mail <action> --channel offline --expected-binding-id <binding_id>`, or the explicit selected-agent equivalent. Keep the same channel and binding through replies and archive.

Ordinary workflows do not read SQLite, scrape tmux variables, reconstruct paths from references, or edit message projections. For deliberate host-local maintenance with an explicit root, switch to `houmao-shared-routines->houmao-mailbox-mgr`. The [layout reference](../filesystem-layout.md) describes storage, not an alternative remote access protocol.

Reading marks a message read; replying marks its parent read and answered. Archive is the explicit completion step after successful work and any required reply. Periodic reminders continue while eligible inbox work remains.

The selected offline sender address remains the offline address even when the agent has an online canonical mail identity. Recipients must belong to the same registry. Reject mixed-channel batches instead of bridging or translating addresses. A submission-only manager result needs authoritative verification before assuming delivery succeeded.

On an isolated registry binding with protected filtering, the writer files matching arrivals directly in Archive. Report completed Inbox work for separately authorized owner filing when ordinary archive is unavailable.
