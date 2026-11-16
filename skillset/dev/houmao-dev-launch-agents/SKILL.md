---
name: houmao-dev-launch-agents
description: Use when a Houmao maintainer explicitly invokes this development skill for local test-fixture setup, DeepSeek or self-hosted API configuration, imported native login, Claude Code/Codex/Kimi Code/DSH test launches, or normal-account online mail qualification on a managed test agent.
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

# Houmao Development Agent Launcher

## Workflow

1. **Select a routine** from **Subcommands** using the developer's requested setup or test launch. For `help`, explain the routes and stop without setup or launch.
2. **Resolve the client and credential selection** through [references/credential-resolution.md](references/credential-resolution.md). A named DeepSeek service selects `cloud-api`; model and client choices remain explicit.
3. **Prepare local inputs** using `configure-fixtures` when prerequisites or selected credentials are missing. Configuration alone does not launch clients or contact a model API.
4. **Execute a requested launch** using [references/common-launch.md](references/common-launch.md). Preserve its raw or managed ownership, mode, workdir, and permission contract. Skip this step for setup-only requests.
5. **Verify and hand off** the configuration result or actual launch identity, private evidence paths, and scoped cleanup command when applicable. Report unavailable inputs and failed launches explicitly.

If the task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the selected routine, fixture interfaces, and constraints, then execute the plan.

## Scope

This manually invoked development skill owns local test-fixture configuration and test-agent launch preparation. It supports explicit API cases and imported native login for Claude Code, Codex, and Kimi Code. DSH uses headless ACP on raw, manager, or passive-server surfaces and native Web for the raw/manager `tui` posture. Native login remains unsupported for DSH. Web and ACP qualification remain separate. It does not administer production agents or create provider accounts, API keys, or interactive logins.

The provider-specific commands retain their raw TUI contract for recorder and behavior-test callers. `launch-fixture` also covers raw headless execution and explicitly selected manager or passive-server test surfaces. Launching a raw client does not establish a Houmao managed identity. Test oracles, recording, skill-pack installation, and behavior adjudication remain owned by their calling workflows.

## Subcommands

These are peer routines; each can consume already configured inputs. Read only the selected detail page and its required shared references.

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `configure-fixtures` | Prepare local API settings or import explicitly selected native auth without launching | [commands/configure-fixtures.md](commands/configure-fixtures.md) |
| `launch-codex` | Launch a raw Codex TUI with selected fixture inputs | [commands/launch-codex.md](commands/launch-codex.md) |
| `launch-claude-code` | Launch a raw Claude Code TUI with selected fixture inputs | [commands/launch-claude-code.md](commands/launch-claude-code.md) |
| `launch-kimi-code` | Launch a raw Kimi Code TUI with selected fixture inputs | [commands/launch-kimi-code.md](commands/launch-kimi-code.md) |
| `launch-fixture` | Prepare and launch an explicit raw, manager, or passive-server test lane | [commands/launch-fixture.md](commands/launch-fixture.md) |
| `attach-online-mail` | Attach a selected existing normal mail account to an active managed test agent without body restart | [commands/attach-online-mail.md](commands/attach-online-mail.md) |
| `help` | Explain prerequisites, API/native choices, supported surfaces, and outputs without launching | This entrypoint |

## Invocation Contract

Use `houmao-dev-launch-agents->configure-fixtures()` for local setup, `houmao-dev-launch-agents->launch-fixture()` for a selected test surface, or a provider-specific launch routine for raw TUI testing. Natural-language requests and the existing `$houmao-dev-launch-agents use <subcommand> ...` form may select the same declared routines.

For a managed mail test, follow `houmao-dev-launch-agents->attach-online-mail()` after launch. Model API authentication and normal-account mail authentication are independent selected inputs.

Default a provider-specific launch to raw TUI and unattended posture. For `launch-fixture`, resolve the surface and mode from the test subject; ask when that distinction is material and unspecified. A setup-only request ends after offline configuration checks.

## Guardrails

- DO NOT expose keys, tokens, auth JSON, or resolved secret env values in chat, OS arguments, tmux commands, reports, or tracked files.
- DO NOT place credential-bearing env files, generated provider homes, prepared fixture projects, or private run state inside the checkout, including repository-local evidence directories.
- DO NOT substitute ambient login, a personal wrapper, or another API case when the selected route is missing an input or fails.
- DO NOT guess a model, context window, capability, resume target, or initial prompt without user delegation or selected configuration.
- DO NOT log in, refresh auth during discovery, copy a complete personal home, or replace an imported bundle without explicit selection and replacement intent.
- DO NOT kill, reuse, or modify sessions or authorities outside the captured run ownership.
- Every tmux test, inspection, and cleanup command must explicitly select its unique isolated server with `-L` or `-S`, after clearing inherited `TMUX` and `TMUX_PANE`. The shared localhost/default server is off limits.
- DO NOT claim passive-server TUI birth, managed identity for a raw client, or successful qualification from configuration checks alone.
- DO NOT route new launches through retired `brains`, `blueprints`, `api-creds`, or legacy demo trees, or add unsupported Gemini CLI launches.
