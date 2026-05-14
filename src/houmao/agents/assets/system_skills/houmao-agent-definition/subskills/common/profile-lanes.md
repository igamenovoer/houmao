# Profile Lanes

Houmao has two reusable birth-time profile lanes. They share some storage and projection shape, but the authoring commands stay lane-bounded.

## Easy Profile

- Skill subcommand: `profiles`.
- Command family: `houmao-mgr project easy profile ...`
- Source kind: one project-easy specialist.
- Typical use: a durable launchable profile over a specialist.
- Launch path: `houmao-mgr project easy instance launch --profile <profile>`.
- Owner in this skill: [subskills/easy/profiles.md](../easy/profiles.md) and [subskills/easy/create-agent-fast-forward.md](../easy/create-agent-fast-forward.md).
- Default routing: loose `profile`, `agent profile`, `launch profile`, or `ready profile` wording means this lane unless the user explicitly asks for raw or recipe-backed behavior.

## Raw Profile

- Skill subcommand: `raw-profiles`.
- Command family: `houmao-mgr project agents launch-profiles ...`
- Source kind: one low-level recipe.
- Typical use: precise recipe-backed build and launch defaults.
- Launch path: `houmao-mgr agents launch --launch-profile <profile>`.
- Owner in this skill: [subskills/low-level/raw-profiles.md](../low-level/raw-profiles.md).
- Routing: use this lane only when the user explicitly says `raw-profiles`, raw profile, recipe-backed profile, or exact `project agents launch-profiles`.

## Shared Rules

- Both lanes may project into `.houmao/agents/launch-profiles/<name>.yaml`.
- Use the command family that matches the stored lane.
- Use `set` for ordinary patch edits.
- Use create with `--yes` only when the user intends same-name replacement.
- Do not replace an easy profile with a raw profile, or the reverse.
