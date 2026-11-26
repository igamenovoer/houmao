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

# Platform Boundaries

Use this reference whenever generated pro loops interact with Houmao platform mechanics rather than loop-local contracts. Generated loop material owns loop semantics; maintained Houmao routines and CLIs own platform mechanics.

## Maintained Skill Ownership

- `houmao-shared-routines->houmao-agent-definition`: specialists, project profiles, `project skills` registration, launch dossiers, credential routing, and `system_skills` pack policy (`houmao-mgr project ...`).
- `houmao-shared-routines->houmao-utils-workspace-mgr`: multi-agent workspace `plan`, `create`, `validate`, and `summarize` operations (`in-repo-workspace` and `out-of-repo-workspace`).
- `houmao-shared-routines->houmao-agent-instance`: live agent `launch`, `join`, `relaunch`, `stop`, `cleanup`, `--executor` target selection, and `agents external` registration.
- `houmao-shared-routines->houmao-agent-access`: gateway admission policy (`open` vs `keyed`), 6-group `default-group` ladder, roles/templates, grants, peer keys, and `self-key` rotation/revocation.
- `houmao-shared-routines->houmao-agent-files`: authorized gateway file reads, patches, uploads, and `publish` (`agents self files push --when-idle`) across `workspace`, `memory`, `skills`, and `mcp` mounts.
- `houmao-shared-routines->houmao-mailbox-mgr`: offline mailbox provisioning/repair/cleanup/export and `agents single|self mailbox online` Stalwart JMAP bindings.
- `houmao-shared-routines->houmao-agent-email-comms` and `houmao-shared-routines->houmao-process-emails-via-gateway`: ordinary mail `status`/`list`/`read`/`peek`/`send`/`post`/`reply`/`mark`/`move`/`archive` and bounded gateway notifier rounds.
- `houmao-shared-routines->houmao-agent-messaging`: live peer/self `request`, `prompt`, `interrupt`, and mailbox handoff routing.
- `houmao-shared-routines->houmao-agent-gateway`: gateway lifecycle, notifier/reminder services, web-entry/dashboard, `open-browser`, and optional gateway plugins such as `houmao-cccc`.
- `houmao-shared-routines->houmao-adv-usage-pattern`: multi-agent gateway/mailbox loop patterns and `houmao-cccc` group-chat push/pull/queue coordination patterns.
- `houmao-shared-routines->houmao-memory-mgr`: birth-time memo seeds and live `pages/` memory operations.
- `houmao-shared-routines->houmao-agent-inspect`: read-only liveness, `state` (`headless`, `service`, `tui`, `web`), logs, usage records, artifacts, and socket-qualified `tmux -S` inspection.

## Generated Material Ownership

- `execplan/specs/`: loop machine contracts, schemas, and templates.
- `execplan/skills/`: generated role instructions, on-event handlers, on-tick handlers, and `<loop-slug>-operator-control`.
- `execplan/agents/`: participant-to-agent bindings, prompt sources, generated skill mounts, `system_skills` preinstall expectations, workspace policy, and notifier prompt paths.
- `execplan/harness/`: loop-local deterministic validation, lookup, template rendering, state initialization/query, and controlled record application.
- `execplan/docs/`: generated human support views.

## Execution Stage, Mail, And Plugin Boundaries

- **Workspace and launch**: `prepare-agents` resolves concrete profile and agent facts without launching agents or mutating workspaces; `prepare-workspace` adapts workspace contracts (`shared-kb/`, `owner-states/<subdir>/`, per-agent `states/`) to `houmao-shared-routines->houmao-utils-workspace-mgr` (or verifies explicit manual evidence); `validate-loop` performs read-only readiness checks; `launch-agents` starts live participants; `start` sends the initial trigger.
- **Mail, access, files, and `houmao-cccc`**: generated skills and harnesses may define message families, schemas, templates, reply expectations, and loop-local state transitions, and may reference `houmao-cccc` group rooms when configured on the gateway, but must never implement custom mailbox storage, ad hoc gateway discovery, custom permission stores, direct unmanaged cross-agent file edits, or local substitutes for `houmao-agent-email-comms`, `houmao-agent-access`, `houmao-agent-files`, or `houmao-cccc` plugin routes.
- **Operator control**: `<loop-slug>-operator-control` and generated harnesses record loop-local control intent and run state while delegating notifier toggles to `houmao-shared-routines->houmao-agent-gateway`, live prompts/requests to `houmao-shared-routines->houmao-agent-messaging`, and mail transport to `houmao-shared-routines->houmao-agent-email-comms`.
