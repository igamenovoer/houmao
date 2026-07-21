# Development Skills

## Purpose

Reusable skill packages and workflows for AI assistants working on the Houmao repository. These skills support development of Houmao itself and are not published as Houmao runtime skills.

## Conventions

- Prefer one directory per skill.
- Include `SKILL.md` as each skill package entrypoint.
- Optionally include `references/`, `agents/`, templates, scripts, or metadata.

## Testing Skill Boundaries

Use the development testing skills according to their oracle:

| Skill | Use For | Do Not Use As |
| --- | --- | --- |
| `houmao-dev-behavior-testing` | Live qualification of system-skill activation, non-activation, actor routing, gates, effects, and semantic outcomes in isolated provider contexts | TUI tracked-state ground truth or an automatic runtime test suite |
| `houmao-dev-tui-testing` | High-rate TUI recording, blind public-state labels, tracker replay, cadence comparison, and review video | Proof that a system skill root activated |
| `houmao-dev-launch-agents` | Secret-safe raw Claude Code, Codex, or Kimi Code launch in a verified tmux session | Houmao managed-agent lifecycle or behavior adjudication |
| `terminal-recorder-workflow` | Recording and replay mechanics for an existing terminal session | Provider launch, system-skill routing, or semantic verdicts |

Behavior qualification may retain terminal evidence, and TUI qualification may drive a task, but their verdicts remain separate. Neither development skill is part of the packaged Houmao admin or agent system-skill packs.
