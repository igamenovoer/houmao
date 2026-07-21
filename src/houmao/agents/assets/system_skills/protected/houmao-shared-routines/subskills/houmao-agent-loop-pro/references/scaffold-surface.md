# Scaffold Surface

## Purpose

Use this page whenever a routed subskill needs to create scaffold-owned starter files or directories.

## Rules

- Use the packaged scaffold generator under `scripts/scaffold.py`.
- Treat `assets/scaffolds/` as the authoritative starter source.
- Run the generator with `pixi run python` when executing it from this repository.
- Do not restate scaffold-owned starter file bodies in routed pages.
- Later stages may revise scaffold-owned generated files when the route explicitly owns that update.

## Profiles

- `intention-create`: creates `intention/README.md` and `intention/loop-overview.md`.
- `intention-init`: creates `intention/README.md`, `intention/loop-overview.md`, and `intention/project-context.md`.
- `execplan-shell`: creates the standard `execplan/` directory shell, starter `README.md` files, and `manifest.toml` seed.
- `execplan-stepwise-shell`: creates the same execplan shell plus `execplan/adrs/`.
- `execplan-finalize-docs`: creates scaffold-owned `execplan/README.md` and named docs starters under `execplan/docs/`.
- `execplan-adr`: creates one `execplan/adrs/<index>-<slug>.md` record from the shared ADR template.

## Intention Profiles

- Use `intention-init` for default `init`.
- `init` owns `intention/project-context.md`.
- Project context may come from:
  - explicit user-provided project root;
  - user-provided project context text;
  - lightweight nearby project detection.
- Use `intention-create` only for the basic editable intention source area without project-context detection.

## Execplan Profiles

- Use `execplan-shell` before one-pass execplan generation.
- Use `execplan-stepwise-shell` before interactive stage generation that records accepted decisions under `execplan/adrs/`.
- Use `execplan-finalize-docs` only for final docs and package README starter material.
- Use `execplan-adr` for accepted step-by-step generation decisions.

## Source And Output

- `intention/` is editable source material.
- `execplan/` is generated operational material.
- Do not treat `execplan/` as the user-editable source of truth.
