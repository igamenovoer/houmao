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

# Launch Agent Instance

## Workflow

1. **Confirm the project-scoped launch source**: `--profile <profile>` (specialist-backed project profile) or `--specialist <specialist> --name <agent-name>` (mutually exclusive). Ask with `Required`/`Optional` labels if source or required identity is missing.
2. **Route manual mailbox-flag launches**: if the caller passes explicit `--mail-transport`, `--mail-root`, or `--mail-account-dir` birth flags rather than relying on stored profile defaults, route to `houmao-shared-routines->houmao-agent-definition->launch-agent()`.
3. **Select only explicitly requested overrides** from **Launch Options** below (omitting `--mode` or `--tmux-server` when stored profile or tool defaults should govern; see [Qualified Run Modes](../../houmao-agent-definition/references/common/profile-lanes.md#qualified-run-modes)).
4. **Execute `houmao-mgr project agents launch`** using the parent's resolved launcher.
5. **Report the launched identity and surface handoff**: tmux session/socket (`tui`), managed control reference (`headless` or `service`), or browser origin (`web`, noting `agents single ... open-browser` for local Kimi Web owners and `houmao-shared-routines->houmao-agent-gateway->web-entry()` for gateway Web links). Direct follow-up messaging to `houmao-shared-routines->houmao-agent-messaging` and inspection to `houmao-shared-routines->houmao-agent-inspect`.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Launch Options** and the user request, then execute the plan.

## Command Shapes and Launch Options

```bash
<chosen houmao-mgr launcher> project agents launch --profile <profile> [--name <agent-name>] [options]
<chosen houmao-mgr launcher> project agents launch --specialist <specialist> --name <agent-name> [options]
```

| Option | Applies To | Behavior |
| --- | --- | --- |
| `--name <agent-name>` | `--specialist` (required), `--profile` (optional override) | Friendly managed-agent instance name. |
| `--agent-id <id>` \| `--agent-id-mode [uuid\|name-hash]` | `--profile`, `--specialist` | Explicit opaque ID or deterministic `name-hash` creation mode (`uuid` default; mutually exclusive). |
| `--mode [headless\|service\|tui\|web]` | `--profile`, `--specialist` | One-shot run mode override (`Claude`: `headless\|tui`; `Codex`: `headless\|service\|tui`; `Kimi`: `headless\|service\|tui\|web`; `DSH`: `headless\|service\|web`). |
| `--headless-display-style [plain\|json\|fancy]`, `--headless-display-detail [concise\|detail]` | `--profile`, `--specialist` | Live pane display overrides for `headless` launches. |
| `--tmux-server [user-default\|houmao-default\|new\|socket]`, `--tmux-socket-path <abs-path>` | `--profile`, `--specialist` | Owner-side tmux server selection (`socket` requires an existing server at `--tmux-socket-path`); recorded at birth for later control and `relaunch`. |
| `--session-name <name>`, `--workdir <dir>` | `--profile`, `--specialist` | Tmux session name on the selected server; runtime cwd (`--workdir` never changes the active `.houmao/` overlay). |
| `--executor <profile>` | `--profile`, `--specialist` | Trusted execution-owner context profile (operator locators managed via `admin executors reconcile\|forget`). |
| `--reuse-home` | `--profile`, `--specialist` | Restart on a compatible stopped preserved home for the resolved managed identity. |
| `--force [keep-stale\|clean]` | `--profile`, `--specialist` | Replace an existing fresh live owner of the resolved identity (`--force` defaults to `keep-stale`). |
| `--auth <cred>`, `--model <m>`, `--reasoning-level <n>`, `--env-set <K=V\|K>` | `--profile`, `--specialist` | One-shot auth, model, reasoning, or environment overrides without mutating the stored profile. |
| `--no-gateway`, `--gateway-port <port>`, `--gateway-background`, `--gateway-admin-seed <file>` | `--profile`, `--specialist` | Gateway birth overrides (foreground auxiliary window by default; pass `--gateway-background` only on explicit request; `--gateway-admin-seed` seeds initial admin public keys). |
| `--managed-header` / `--no-managed-header`, `--managed-header-section SECTION=enabled\|disabled` | `--profile`, `--specialist` | One-shot `MANAGED_PROMPT_HEADER_VERSION = 2` overrides. |
| `--tool-params JSON-OR-@PATH` | `--profile`, `--specialist` | Layered per-tool parameters for this instance (including `tool_params.permissions`). |

## Guardrails

- DO NOT guess `--profile` vs `--specialist`, names, or optional overrides, or reject `--profile` launches merely because the stored profile declares mailbox or gateway defaults.
- DO NOT pass `--gateway-background`, `--force`, or `--reuse-home` unless the caller explicitly requested that behavior, or add raw Kimi `--auto`/`--yolo` flags in place of unattended prompt mode.
- DO NOT describe `--workdir` as changing the selected `.houmao/` overlay, runtime root, or mailbox root.
