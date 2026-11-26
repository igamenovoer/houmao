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

# Launch Agents

Launch prepared lite loop participants into live sessions after `validate-loop` passes and before `start` delivers the first trigger.

## Read First

- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

## Workflow

1. Require `<loop-dir>`, a current `validate-loop` readiness pass, and prepared participant facts from `prepare-agents` (plus workspace readiness evidence when workspaces are required).
2. Confirm each participant has a concrete agent/profile, qualified `--mode` (`headless`, `service`, `tui`, `web`), credential, workdir, generated skills, and memo posture, and is not already live in an incompatible mode, `--tmux-server`, cwd, or mailbox posture.
3. Launch missing live participants via `houmao-shared-routines->houmao-agent-instance` or `houmao-mgr project agents launch`, passing explicit `--mode` (`headless`, `service`, `tui`, `web`), `--tmux-server` (`user-default`, `houmao-default`, `new`, `socket` when TUI-backed), and `--executor` when applicable.
4. Verify live status and session/binding facts via `houmao-shared-routines->houmao-agent-inspect` without sending loop-start prompts or mail.
5. Report launched vs already-live agents, modes, `--tmux-server`/session ids, cwd, mailbox posture, launch surface used, warnings for `start`, and whether `start` may proceed.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Guardrails

- DO NOT create or repair specialists, profiles, workspaces, mailboxes, gateways, memories, or `execplan/` Markdown during `launch-agents`.
- DO NOT launch when `validate-loop` readiness evidence is missing or stale, and DO NOT send initial loop triggers or task prompts before `start`.
- DO NOT instruct launched agents to wait, sleep, or poll in-chat for future mail or ticks.
