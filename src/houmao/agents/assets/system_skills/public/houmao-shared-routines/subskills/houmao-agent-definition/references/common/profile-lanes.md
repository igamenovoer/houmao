# Profile Lanes

Houmao has two reusable birth-time profile lanes. They share some storage and projection shape, but the authoring commands stay lane-bounded.

## Project Profile

- Skill subcommand: `profiles`.
- Command family: `houmao-mgr project profile ...`
- Source kind: one project specialist.
- Typical use: a durable launchable profile over a specialist.
- Launch path: `houmao-mgr project agents launch --profile <profile>`.
- Owner in this skill: [commands/easy/profiles.md](../../commands/easy/profiles.md) and [commands/easy/create-agent-fast-forward.md](../../commands/easy/create-agent-fast-forward.md).
- Default routing: loose `profile`, `agent profile`, `project profile`, or `ready profile` wording means this lane unless the user explicitly asks for native-agent launch-dossier behavior.

## Launch Dossier

- Skill subcommand: `launch-dossiers`.
- Command family: `houmao-mgr internals native-agent launch-dossiers ...`
- Source kind: one low-level recipe.
- Typical use: precise recipe-backed build and launch defaults.
- Launch path: project-backed birth uses `houmao-mgr project agents launch --profile <profile>`; launch dossiers are low-level authoring inputs and do not have a maintained public root-level managed-agent launch path.
- Owner in this skill: [commands/low-level/launch-dossiers.md](../../commands/low-level/launch-dossiers.md).
- Routing: use this lane only when the user explicitly says `launch-dossiers`, launch dossier, or exact `internals native-agent launch-dossiers`.

## Shared Rules

- Both lanes may project into `.houmao/agents/launch-profiles/<name>.yaml`.
- Use the command family that matches the stored lane.
- Use `set` for ordinary patch edits.
- Use create with `--yes` only when the user intends same-name replacement.
- Do not replace a project profile with a launch dossier, or the reverse.
