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

Launch prepared loop participants into live runtime sessions after `validate-loop` passes and before `start` delivers initial loop work.

## Read First

- [../../references/generated-contract-defaults.md](../../references/generated-contract-defaults.md)
- MUST READ: [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

## Workflow

1. Require `<loop-dir>`, `<loop-dir>/execplan/manifest.toml`, current `validate-execplan` and `validate-loop` pass evidence, prepared launch facts from `prepare-agents`, and workspace readiness evidence from `prepare-workspace` (when workspaces are used).
2. Verify every required participant has a concrete agent id, project profile (or explicit raw profile), tool (`claude`, `codex`, `kimi`, `dsh`), qualified `--mode` (`headless`, `service`, `tui`, `web`), launch cwd, memo seed posture (`MANAGED_PROMPT_HEADER_VERSION = 2` `<houmao_managed_header>` and `<memo_cue>` injection), installed generated skills, `system_skills` pack posture, and notifier prompt posture when mail-driven.
3. Confirm no required participant is already live with an incompatible mode, executor, `--tmux-server`, cwd, profile, or mailbox binding.
4. Launch missing live participants via `houmao-shared-routines->houmao-agent-instance` or `houmao-mgr project agents launch`, passing explicit `--mode` (`headless`, `service`, `tui`, `web`), `--tmux-server` (`user-default`, `houmao-default`, `new`, `socket` when TUI-backed), and `--executor` when targeting a named or remote executor (including ACP-backed `dsh` `headless`/`service`/`web` sessions).
5. Confirm liveness, session/binding identity, and gateway/mailbox attachment through `houmao-shared-routines->houmao-agent-inspect` without sending loop-start prompts or mail.
6. Report launched vs already-live agents, concrete agent ids, profiles, modes, executor/tmux-server bindings, session ids, cwd, mailbox posture, launch surfaces used, unlaunched blockers, and whether `start` may proceed.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Guardrails

- DO NOT create or repair specialists, profiles, skills, `system_skills` packs, workspaces, mailboxes, gateways, memories, harness state, or `execplan/` files during `launch-agents`.
- DO NOT invoke `prepare-agents`, `prepare-workspace`, or `validate-loop` implicitly or launch when pre-launch readiness evidence is missing or stale.
- DO NOT send initial loop triggers, generated mail, or task prompts here; reserve trigger delivery for `start`.
- DO NOT instruct launched agents to wait, sleep, or poll in-chat for future mail or tick events.
