# Profile Lanes

Houmao has two reusable birth-time profile lanes. They share some storage and projection shape, but the authoring commands stay lane-bounded.

## Easy Profile

- Command family: `houmao-mgr project easy profile ...`
- Source kind: one project-easy specialist.
- Typical use: a durable, ready-to-launch profile over a specialist.
- Launch path: `houmao-mgr project easy instance launch --profile <profile>`.
- Owner in this skill: [subskills/easy/profiles.md](../easy/profiles.md) and [subskills/easy/create-ready-agent-profile.md](../easy/create-ready-agent-profile.md).

## Explicit Launch Profile

- Command family: `houmao-mgr project agents launch-profiles ...`
- Source kind: one low-level recipe.
- Typical use: precise recipe-backed build and launch defaults.
- Launch path: `houmao-mgr agents launch --launch-profile <profile>`.
- Owner in this skill: [subskills/low-level/launch-profiles.md](../low-level/launch-profiles.md).

## Shared Rules

- Both lanes may project into `.houmao/agents/launch-profiles/<name>.yaml`.
- Use the command family that matches the stored lane.
- Use `set` for ordinary patch edits.
- Use create with `--yes` only when the user intends same-name replacement.
- Do not replace an easy profile with an explicit launch profile, or the reverse.
