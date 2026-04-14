# Development Setup

This repository extends the local Codex skill registry at `.codex/skills/` with symlinks into `magic-context/skills/`. The goal is to make shared skills available to the project without copying their contents into the repo-local Codex skill directory.

## How `.codex/skills/` is structured

- Project-local skills already live directly under `.codex/skills/`, including the OpenSpec workflow skills and the `.system/` built-ins.
- Additional shared skills are exposed as symlinks that point back into `magic-context/skills/`.
- Each symlinked skill keeps its canonical source in `magic-context`, so updates there are reflected automatically in `.codex/skills/`.

## Symlinked skills introduced from `magic-context`

### From `magic-context/skills/cli-agents/`

- `claude-code-install`
- `claude-code-invoke-once`
- `claude-code-invoke-persist`
- `codex-cli-install`
- `copilot-invoke-once`

### From `magic-context/skills/devel/`

- `do-interactive-test`
- `hack-through-testing`
- `impl-via-git-worktree`

### From `magic-context/skills/openspec-ext/`

- `openspec-ext-explain`
- `openspec-ext-hack-through-test`
- `openspec-ext-respond-to-review`
- `openspec-ext-review-plan`
- `openspec-ext-revise-by-decision`

### From `magic-context/skills/writing/`

- `make-program-tutorial`
- `mermaid-graphing`

## Current target location

All of the skills above are available through `.codex/skills/` as relative symlinks. For example:

- `.codex/skills/claude-code-install -> ../../magic-context/skills/cli-agents/claude-code-install`
- `.codex/skills/do-interactive-test -> ../../magic-context/skills/devel/do-interactive-test`
- `.codex/skills/openspec-ext-review-plan -> ../../magic-context/skills/openspec-ext/openspec-ext-review-plan`
- `.codex/skills/make-program-tutorial -> ../../magic-context/skills/writing/make-program-tutorial`

## Notes

- `.codex/skills/README.md` is also currently symlinked to `magic-context/skills/writing/README.md`. It is a supporting file, not a skill directory.
- A skill is considered usable from `.codex/skills/` when its `SKILL.md` is reachable through the symlinked path.
