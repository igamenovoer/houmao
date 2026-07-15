---
name: houmao-dev-launch-agents
description: Use when a Houmao maintainer explicitly invokes this development skill to launch a local Codex, Claude Code, or Kimi Code TUI agent in tmux, select native auto credentials, or resolve the ordered Claude launcher and Kimi-compatible `.env` fallbacks.
---

# Houmao Development Agent Launcher

## Overview

Launch one local provider TUI in a fresh tmux session with a reproducible, secret-safe record of the selected executable and credential strategy. This is a manual development skill; do not invoke it implicitly for ordinary agent lifecycle work.

## When to Use

Use this skill for repository development, smoke testing, TUI observation, or recorder setup that needs a raw Codex, Claude Code, or Kimi Code process. Use the maintained Houmao demo alternatives when the generated home, gateway, recorder, or managed-agent pipeline is itself under test.

Do not use it for production lifecycle administration, credential creation or login, headless-only prompts, Gemini CLI, or launching through retired `brains`, `blueprints`, `api-creds`, or legacy demo trees.

## Workflow

1. **Resolve common launch inputs.** Determine the repository root, trusted workdir, fresh run root, unique tmux session, optional initial arguments, and requested `unattended` or explicit `as_is` posture from [references/common-launch.md](references/common-launch.md).
2. **Select the provider subcommand** from **Subcommands**; do not infer a provider when the request is ambiguous.
3. **Resolve the executable and credential strategy** using the selected command page and [references/credential-resolution.md](references/credential-resolution.md).
4. **Launch the TUI in tmux** without exposing secret values in command output, process arguments, metadata, or logs.
5. **Verify the live provider process and report evidence.** A created tmux session alone is not a successful launch.

If the task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the provider subcommands, credential precedence, and common launch constraints, then execute the plan.

## Invocation Contract

Preferred forms are `$houmao-dev-launch-agents use <subcommand> ...` and `$houmao-dev-launch-agents <provider launch request>`. These are skill subcommands, not shell commands.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `launch-codex` | Launch a Codex TUI with native auto credentials | [commands/launch-codex.md](commands/launch-codex.md) |
| `launch-claude-code` | Launch Claude Code through the ordered local launcher and credential fallback chain | [commands/launch-claude-code.md](commands/launch-claude-code.md) |
| `launch-kimi-code` | Launch a Kimi Code TUI with native auto credentials | [commands/launch-kimi-code.md](commands/launch-kimi-code.md) |
| `help` | Explain provider routes, required inputs, credential precedence, and outputs without launching anything | This entrypoint |

## Shared Invariants

- Run from the Houmao repository and place temporary metadata under `tmp/houmao-dev-launch-agents/<run-id>/`.
- Default development and automated-test launches to `unattended`. Use `as_is` only when the user explicitly requests an interactive permission posture.
- Treat `auto` as a credential-discovery strategy, never as a literal credential bundle name or a request to perform login.
- Do not print, log, commit, interpolate into tmux command strings, or include in reports any API key, token, credential JSON, or secret-bearing `.env` value.
- Preserve an existing tmux session. Choose a new session name instead of killing or replacing an unrelated session.
- Keep maintained demo and fixture lanes available, but do not use `scripts/demo/legacy/` or restore old shared credential trees.

## Common Mistakes

- Treating `tmux new-session` exit code zero as proof the provider stayed alive. Verify pane PID, child process, and visible TUI output.
- Passing `.env` secret values on the shell command line. Use a mode-`0700` run-local helper that reads a trusted file as data inside the tmux process.
- Skipping a higher-priority Claude launcher after finding a lower-priority one. Follow the entire ordered resolver and stop at the first usable strategy.
- Running `codex login`, `kimi login`, or `claude auth login` during auto discovery. Report a credential blocker instead.
- Appending a second unattended flag to a Claude wrapper that already owns its launch flags. Invoke the selected wrapper as the launcher.
