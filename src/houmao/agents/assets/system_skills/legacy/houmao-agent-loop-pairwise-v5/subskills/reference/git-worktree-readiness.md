# Git Worktree Readiness

## Purpose

Use this page when a generated loop requires per-agent Git worktrees or when manual workspace evidence claims a Git worktree is ready.

A ready worktree is more than a checked-out branch. It must be a normal Git worktree, have the local project state needed by the task, run the project tools from inside the worktree, expose required shared/local resources, and preserve the workspace isolation expected by the generated contracts.

## Core Rules

- Use normal `git worktree` checkouts from the source repo. Do not copy repositories by hand.
- Validate readiness from inside each agent worktree, not only from the source repo.
- Treat generated workspace contracts and prepared agent/profile facts as the authority for expected path, branch, cwd, memo, and read/write posture.
- Do not replace tracked files or tracked directories with symlinks.
- Symlink untracked source-repo directories into agent worktrees by default, except for protected local state, Git control state, temporary data, and nested worktree directories.
- Do not symlink provider homes, credential directories, trust state, AI-tool local state, Git control state, temporary directories, or nested worktree directories into agent worktrees unless the workspace contract explicitly requires and justifies a narrow exception.
- Repair missing local-only state from the source checkout before using expensive fresh downloads, rebuilds, or independent checkouts.
- Record exact readiness evidence so `validate-loop` can use it.

## Worktree Identity

Check each agent worktree:

```bash
cd "$WT"
git rev-parse --show-toplevel
git status --short
git branch --show-current
git worktree list
```

Ready posture:
- `$WT` is registered as a Git worktree of the intended source repo;
- current branch matches the generated workspace contract or accepted operator plan;
- dirty state is understandable and expected for the current stage;
- no two agents share the same mutable worktree target unless the generated contract explicitly allows it.

## Runtime Environment

The worktree must run the project-managed environment from inside the worktree.

Choose checks from the generated workspace contract first. If the contract is not specific enough, inspect the source repo and worktree for common runtime signals:
- `pixi.toml` or `pixi.lock`: use `pixi run`;
- `pyproject.toml` plus `uv.lock`: use `uv run`;
- `pyproject.toml` plus `poetry.lock`: use `poetry run`;
- `pdm.lock`: use `pdm run`;
- `environment.yml`, `conda-lock.yml`, or `pixi.toml` with conda tasks: use the declared conda, mamba, or pixi surface;
- `package.json` plus `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, or `bun.lockb`: use the matching package-manager exec/run surface;
- `Cargo.toml`: use `cargo metadata` and task-specific cargo commands;
- `Makefile`, `Justfile`, `Taskfile.yml`, or `noxfile.py`: use the declared task runner when the generated contract names a target.

Generic patterns:

```bash
cd "$WT"
pixi run python -c "import sys; print(sys.executable)"
pixi run <project-cli> --help

uv run python -c "import sys; print(sys.executable)"
uv run <project-cli> --help

pnpm exec <project-cli> --help
npm run <named-script> -- --help

cargo metadata --no-deps
just --list
make -n <target>
```

Ready posture:
- the selected environment command is the project-owned path, not an accidental system interpreter;
- dependency-manager commands do not fail from `$WT`;
- imports, CLIs, or smoke checks required by the loop work from `$WT`;
- task runners can list or dry-run the named target when dry-run/list mode exists;
- failures are task/tool failures, not missing environment, broken cwd, missing local state, or import-path surprises.

If the environment works from the source repo but not the worktree, repair the worktree from source-repo state first.

## Submodules

Tracked submodules that the loop needs must be materialized inside each worktree. Populated submodules in the source repo do not automatically make a new worktree ready.

Generic checks:

```bash
cd "$WT"
git submodule status --recursive
```

Ready posture:
- required submodule paths are not empty placeholders;
- submodule commits match the superproject or accepted workspace plan;
- agents that may commit in submodules have clear branch and gitlink-update rules;
- agents do not add, remove, or reconfigure submodules unless the generated contract explicitly assigns that work.

Prefer workspace-manager supported submodule handling. Do not hand-roll submodule materialization when the workspace manager can represent it.

## Untracked Directory Symlinks

By default, preserve source-repo local context by symlinking untracked directories from the source checkout into each agent worktree. This keeps local datasets, caches, reference checkouts, generated indexes, local catalogs, and similar project state visible without per-agent duplication.

Skip these untracked directories by default:
- AI/tool/provider local state, such as `.codex/`, `.claude/`, `.agents/`, `.github/`, `.gemini/`, `.aider/`, `.cursor/`, `.continue/`, `.windsurf/`, and `.kiro/`;
- Git control state, including `.git/` or `.git` files;
- temporary data directories, such as `tmp/`, `temp/`, and clearly equivalent scratch directories;
- nested worktrees or repository checkouts that sit inside the source repo tree, such as existing task worktrees under a workspace root.

Rules:
- discover untracked directories from the source checkout without following symlinks;
- skip a directory if Git tracks any file under it;
- skip a directory if it is itself a Git worktree or repository checkout;
- skip a directory if linking it would point an agent at another agent's mutable workspace;
- use relative symlinks when practical;
- record every linked and skipped directory, including the skip reason, in workspace evidence.

## Local-Only State

Many projects need local-only state that is not tracked by Git, such as datasets, reference checkouts, caches, generated indexes, local catalogs, or benchmark assets.

Ready posture:
- required local-only paths are visible from `$WT`;
- eligible untracked directories are symlinked into `$WT` by default;
- protected local state, Git control state, temporary data, and nested worktree directories are skipped unless the workspace contract explicitly permits a narrow exception;
- payload files are concrete usable files, not placeholder pointers or empty directories;
- symlink targets are intentional, stable, and recorded in workspace evidence;
- skipped symlink candidates are recorded with reasons.

When checking large payloads, use a project-specific probe that detects placeholder files, missing data, or broken links. Do not assume directory existence is enough.

## Project Configuration Parity

If project behavior depends on catalogs, registries, local overrides, workload definitions, variant indexes, tool profiles, or environment config, compare semantic resolution from the source repo and the worktree.

Generic pattern:

```bash
cd "$ROOT"
<env-tool> run <project-cli> <config-list-command> > /tmp/root-config.txt

cd "$WT"
<env-tool> run <project-cli> <config-list-command> > /tmp/worktree-config.txt

diff -u /tmp/root-config.txt /tmp/worktree-config.txt
```

Ready posture:
- the worktree resolves the same task-relevant definitions as the source repo;
- differences are intentional and recorded;
- command behavior, not only textual config equality, is checked when resolution depends on local overrides or environment.

## Task Tooling

The tools an agent will use must be tested from the worktree before launch.

Check surfaces named by the generated workspace or run contracts:
- build or test commands;
- project CLIs;
- data/catalog listing commands;
- artifact or variant management commands;
- evaluation or smoke-test commands;
- read/write paths for outputs and scratch files.

Ready posture:
- commands can find their config, inputs, and writable outputs from `$WT`;
- expected task-level failures are distinguishable from workspace failures;
- the report names commands that passed, commands that failed, and why failures do or do not block launch.

## Readiness Report

For each worktree, report:
- source repo root and worktree path;
- branch name and `git status --short` posture;
- launch cwd that profiles will use;
- submodule posture;
- local-only state links or mounts;
- project runtime/tool smoke checks;
- config parity checks;
- payload/cache readiness checks;
- writable and read-only path boundaries;
- unresolved blockers and warnings.

`validate-loop` should treat missing or stale worktree evidence as a blocker before `launch-agents`.
